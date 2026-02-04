"""
Timeout Checker Lambda Function

Periodically checks active sessions for inactivity timeouts and stops Spotify
playback when users leave the bathroom without further motion detected.

Flow:
1. Scan active sessions from DynamoDB (status='active')
2. For each active session:
   - Retrieve sensor and user configuration
   - Calculate elapsed time since lastMotionTime
   - If timeout exceeded:
       * Retrieve Spotify access token
       * Check playback state
       * Pause Spotify playback if still playing
       * Mark session completed and save stats
3. Log summary statistics

Environment Variables:
- SESSIONS_TABLE: DynamoDB Sessions table name
- SENSORS_TABLE: DynamoDB Sensors table name
- USERS_TABLE: DynamoDB Users table name
- SPOTIFY_DEFAULT_TIMEOUT_MINUTES: Default timeout (minutes)
- LOG_LEVEL: Logging level

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2.4)
"""

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from boto3.dynamodb.conditions import Attr

from logger import get_logger, log_error, log_performance, add_persistent_context
from dynamodb_helper import DynamoDBHelper
from secrets_helper import get_secret
from spotify_client import SpotifyClient
from exceptions import (
    ValidationError,
    ResourceNotFoundError,
    SpotifyAuthenticationError,
    ConfigurationError
)

logger = get_logger(__name__)

# Environment variables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
SENSORS_TABLE = os.environ.get("SENSORS_TABLE")
USERS_TABLE = os.environ.get("USERS_TABLE")

# Defaults
DEFAULT_TIMEOUT_MINUTES = int(os.environ.get("SPOTIFY_DEFAULT_TIMEOUT_MINUTES", "5"))


def handler(event, context):
    """
    Lambda handler for session timeout checking.

    Args:
        event: EventBridge scheduled event
        context: Lambda context object

    Returns:
        dict: Summary of timeout operations
    """
    start_time = time.time()

    logger.info(
        "Timeout Checker invoked",
        extra={
            "function_name": context.function_name,
            "request_id": context.aws_request_id
        }
    )

    statistics = {
        "active_sessions_checked": 0,
        "sessions_timed_out": 0,
        "playbacks_paused": 0,
        "sessions_completed": 0,
        "sessions_skipped": 0,
        "errors": []
    }

    try:
        validate_environment()

        active_sessions = get_active_sessions()
        statistics["active_sessions_checked"] = len(active_sessions)

        now = datetime.utcnow()

        for session in active_sessions:
            try:
                result = process_session_timeout(session, now)
                if result["skipped"]:
                    statistics["sessions_skipped"] += 1
                if result["timed_out"]:
                    statistics["sessions_timed_out"] += 1
                if result["playback_paused"]:
                    statistics["playbacks_paused"] += 1
                if result["session_completed"]:
                    statistics["sessions_completed"] += 1
            except Exception as exc:
                log_error(logger, exc, "Failed to process session timeout")
                statistics["errors"].append(
                    {
                        "session_id": session.get("sessionId"),
                        "error": type(exc).__name__,
                        "message": str(exc)
                    }
                )

        duration_ms = (time.time() - start_time) * 1000
        log_performance(
            logger,
            "timeout_checker_complete",
            duration_ms,
            success=True,
            **statistics
        )

        return {
            "statusCode": 200,
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": statistics,
            "duration_ms": round(duration_ms, 2)
        }

    except Exception as exc:
        log_error(logger, exc, "Timeout checker failed")
        return {
            "statusCode": 500,
            "error": "InternalError",
            "message": str(exc),
            "statistics": statistics
        }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def validate_environment() -> None:
    """Ensure required environment variables are set."""
    required = ["SESSIONS_TABLE", "SENSORS_TABLE", "USERS_TABLE"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ConfigurationError(
            message=f"Missing required environment variables: {', '.join(missing)}",
            details={"missing_variables": missing}
        )


def get_active_sessions() -> List[Dict[str, Any]]:
    """
    Scan DynamoDB for active sessions.

    Returns:
        List of active session records
    """
    dynamodb = DynamoDBHelper(SESSIONS_TABLE)
    active_sessions: List[Dict[str, Any]] = []
    last_evaluated_key = None

    while True:
        params: Dict[str, Any] = {
            "FilterExpression": Attr("status").eq("active")
        }
        if last_evaluated_key:
            params["ExclusiveStartKey"] = last_evaluated_key

        response = dynamodb.table.scan(**params)
        items = response.get("Items", [])
        active_sessions.extend(items)
        last_evaluated_key = response.get("LastEvaluatedKey")

        if not last_evaluated_key:
            break

    logger.info(
        "Active sessions scan completed",
        extra={"active_sessions": len(active_sessions)}
    )
    return active_sessions


def process_session_timeout(session: Dict[str, Any], now: datetime) -> Dict[str, bool]:
    """
    Process timeout logic for a single session.

    Args:
        session: Session record from DynamoDB
        now: Current UTC time

    Returns:
        Dict with flags for stats aggregation
    """
    result = {
        "skipped": False,
        "timed_out": False,
        "playback_paused": False,
        "session_completed": False
    }

    session_id = session.get("sessionId")
    sensor_id = session.get("sensorId")
    user_id = session.get("userId")

    add_persistent_context(logger, session_id=session_id, sensor_id=sensor_id, user_id=user_id)

    if not session_id or not sensor_id or not user_id:
        raise ValidationError(
            message="Session missing required identifiers",
            field="sessionId/sensorId/userId"
        )

    sensor = get_sensor_config(sensor_id)
    user = get_user_config(user_id)

    timeout_minutes = get_timeout_minutes(sensor)
    last_motion_time = parse_datetime(session.get("lastMotionTime")) or parse_datetime(
        session.get("startTime")
    )

    if not last_motion_time:
        logger.warning("Session missing lastMotionTime/startTime, skipping")
        result["skipped"] = True
        return result

    if not should_timeout(last_motion_time, timeout_minutes, now):
        result["skipped"] = True
        return result

    result["timed_out"] = True

    spotify_token = get_spotify_token(user)
    spotify_client = SpotifyClient(access_token=spotify_token)

    playback_state = spotify_client.get_playback_state()
    playback_paused = pause_playback_if_active(
        spotify_client,
        playback_state,
        sensor
    )

    result["playback_paused"] = playback_paused

    update_session_completed(session, now, playback_paused)
    result["session_completed"] = True

    logger.info(
        "Session timed out and completed",
        extra={
            "session_id": session_id,
            "timeout_minutes": timeout_minutes,
            "playback_paused": playback_paused
        }
    )

    return result


def get_sensor_config(sensor_id: str) -> Dict[str, Any]:
    """Retrieve sensor configuration from DynamoDB."""
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    sensor = dynamodb.get_item({"sensorId": sensor_id})
    if not sensor:
        raise ResourceNotFoundError(
            message=f"Sensor not found: {sensor_id}",
            resource_type="Sensor",
            resource_id=sensor_id
        )
    return sensor


def get_user_config(user_id: str) -> Dict[str, Any]:
    """Retrieve user configuration from DynamoDB."""
    dynamodb = DynamoDBHelper(USERS_TABLE)
    user = dynamodb.get_item({"userId": user_id})
    if not user:
        raise ResourceNotFoundError(
            message=f"User not found: {user_id}",
            resource_type="User",
            resource_id=user_id
        )
    return user


def get_timeout_minutes(sensor: Dict[str, Any]) -> int:
    """Get timeout minutes from sensor config with fallback to default."""
    candidates = [
        sensor.get("timeout_minutes"),
        sensor.get("timeoutMinutes"),
        sensor.get("preferences", {}).get("timeoutMinutes"),
        sensor.get("preferences", {}).get("timeout_minutes")
    ]
    for value in candidates:
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return DEFAULT_TIMEOUT_MINUTES


def parse_datetime(value: Any) -> Optional[datetime]:
    """
    Parse datetime from various formats: ISO string, epoch seconds, datetime.
    Returns a naive UTC datetime.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value)
    if isinstance(value, str):
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            return None
    return None


def should_timeout(last_motion_time: datetime, timeout_minutes: int, now: datetime) -> bool:
    """Determine if session has exceeded timeout."""
    elapsed = now - last_motion_time
    return elapsed >= timedelta(minutes=timeout_minutes)


def get_spotify_token(user: Dict[str, Any]) -> str:
    """Retrieve Spotify access token from Secrets Manager."""
    token_secret_arn = user.get("spotify_token_secret_arn")
    if not token_secret_arn:
        raise SpotifyAuthenticationError(
            message="User has no Spotify token secret configured"
        )
    try:
        tokens = get_secret(token_secret_arn)
        access_token = tokens.get("access_token")
        if not access_token:
            raise SpotifyAuthenticationError(
                message="No access_token in user's Spotify secret"
            )
        return access_token
    except Exception as exc:
        raise SpotifyAuthenticationError(
            message=f"Failed to retrieve Spotify access token: {str(exc)}"
        ) from exc


def pause_playback_if_active(
    spotify_client: SpotifyClient,
    playback_state: Optional[Dict[str, Any]],
    sensor: Dict[str, Any]
) -> bool:
    """
    Pause Spotify playback if currently playing.
    Returns True if a pause was attempted.
    """
    if not playback_state or not playback_state.get("is_playing"):
        logger.info("Playback already stopped or no active playback")
        return False

    device_id = (
        sensor.get("spotify_config", {}).get("device_id") or
        sensor.get("spotifyDeviceId")
    )

    spotify_client.pause_playback(device_id=device_id)
    return True


def calculate_session_duration_minutes(
    start_time: Optional[datetime],
    end_time: Optional[datetime]
) -> Optional[float]:
    """Calculate session duration in minutes."""
    if not start_time or not end_time:
        return None
    duration = end_time - start_time
    return round(duration.total_seconds() / 60, 2)


def update_session_completed(
    session: Dict[str, Any],
    end_time: datetime,
    playback_paused: bool
) -> None:
    """Update session status and statistics in DynamoDB."""
    session_id = session.get("sessionId")
    start_time = parse_datetime(session.get("startTime"))
    duration_minutes = calculate_session_duration_minutes(start_time, end_time)

    updates = {
        "status": "completed",
        "endTime": end_time.isoformat(),
        "durationMinutes": duration_minutes,
        "playbackStopped": playback_paused,
        "updatedAt": datetime.utcnow().isoformat()
    }

    dynamodb = DynamoDBHelper(SESSIONS_TABLE)
    dynamodb.update_item(key={"sessionId": session_id}, updates=updates)

