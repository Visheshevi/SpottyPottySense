"""
Motion Handler Lambda Function

Processes motion detection events from IoT devices and triggers Spotify playback.
This is the CORE function of SpottyPottySense - it orchestrates all components
to provide the automatic music playback experience.

Flow:
1. Parse and validate IoT event
2. Retrieve sensor and user configuration from DynamoDB
3. Check quiet hours (time-based blocking)
4. Check motion debounce (prevent spam triggers)
5. Get or create playback session
6. Retrieve Spotify access token from Secrets Manager
7. Check current Spotify playback state
8. Start Spotify playback if not already playing
9. Update sensor state (lastMotionTime) in DynamoDB
10. Update session (increment motion count)
11. Log motion event to MotionEvents table
12. Return success response

Environment Variables:
- SENSORS_TABLE: DynamoDB Sensors table name
- USERS_TABLE: DynamoDB Users table name
- SESSIONS_TABLE: DynamoDB Sessions table name
- EVENTS_TABLE: DynamoDB MotionEvents table name
- SPOTIFY_CREDENTIALS_SECRET: Spotify client credentials secret ARN
- LOG_LEVEL: Logging level

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2.3)
"""

import os
import time
import uuid
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, Any, Optional, Tuple

# Import from common layer
from logger import get_logger, log_error, log_performance, add_persistent_context
from dynamodb_helper import DynamoDBHelper
from secrets_helper import get_secret
from spotify_client import SpotifyClient
from validation import validate_sensor_data, validate_user_data
from exceptions import (
    ValidationError,
    ResourceNotFoundError,
    SpotifyAPIError,
    SpotifyAuthenticationError,
    DynamoDBError,
    ConfigurationError
)

# Initialize logger
logger = get_logger(__name__)

# Environment variables
SENSORS_TABLE = os.environ.get('SENSORS_TABLE')
USERS_TABLE = os.environ.get('USERS_TABLE')
SESSIONS_TABLE = os.environ.get('SESSIONS_TABLE')
EVENTS_TABLE = os.environ.get('EVENTS_TABLE')
SPOTIFY_CREDENTIALS_SECRET = os.environ.get('SPOTIFY_CREDENTIALS_SECRET')

# Constants
MOTION_DEBOUNCE_DEFAULT_MINUTES = 2
TIMEOUT_DEFAULT_MINUTES = 5


def handler(event, context):
    """
    Lambda handler for motion detection events from AWS IoT Core.
    
    This is the main entry point for processing motion events. It orchestrates
    all the business logic to determine if playback should start and executes
    the appropriate actions.
    
    Args:
        event: IoT Rule event containing motion detection data
        context: Lambda context object
        
    Returns:
        dict: Response with action taken and status
        
    Example Event:
        {
            "sensorId": "bathroom_main",
            "event": "motion_detected",
            "timestamp": 1704412800,
            "metadata": {
                "batteryLevel": 85,
                "signalStrength": -45
            }
        }
        
    Example Response:
        {
            "statusCode": 200,
            "action": "playback_started",
            "sensorId": "bathroom_main",
            "sessionId": "session-123",
            "message": "Playback started successfully"
        }
    """
    start_time = time.time()
    
    logger.info(
        "Motion Handler invoked",
        extra={
            "function_name": context.function_name,
            "request_id": context.aws_request_id
        }
    )
    
    try:
        # Validate environment variables
        validate_environment()
        
        # Parse and validate event
        sensor_id, event_timestamp, metadata = parse_event(event)
        
        # Add persistent context for all subsequent logs
        add_persistent_context(logger, sensor_id=sensor_id)
        
        logger.info(
            f"Processing motion event for sensor: {sensor_id}",
            extra={"timestamp": event_timestamp, "metadata": metadata}
        )
        
        # Step 1: Get sensor configuration
        sensor = get_sensor_config(sensor_id)
        user_id = sensor.get('userId')
        add_persistent_context(logger, user_id=user_id)
        
        # Step 2: Get user configuration
        user = get_user_config(user_id)
        
        # Step 3: Check if sensor is enabled
        if not sensor.get('enabled', True):
            logger.info("Sensor is disabled, ignoring motion event")
            return create_response(
                status_code=200,
                action="ignored",
                message="Sensor is disabled",
                sensor_id=sensor_id
            )
        
        # Step 4: Check quiet hours
        if is_quiet_hours(sensor, event_timestamp):
            logger.info("Motion detected during quiet hours, ignoring")
            return create_response(
                status_code=200,
                action="ignored_quiet_hours",
                message="Motion detected during quiet hours",
                sensor_id=sensor_id
            )
        
        # Step 5: Check motion debounce
        if should_debounce(sensor, event_timestamp):
            logger.info("Motion detected too soon after last trigger, ignoring")
            return create_response(
                status_code=200,
                action="ignored_debounce",
                message="Motion detected within debounce period",
                sensor_id=sensor_id
            )
        
        # Step 6: Get or create session
        session = get_or_create_session(sensor_id, user_id)
        session_id = session.get('sessionId')
        add_persistent_context(logger, session_id=session_id)
        
        logger.info(f"Session retrieved/created: {session_id}")
        
        # Step 7: Get Spotify access token
        spotify_token = get_spotify_token(user)
        
        # Step 8: Check current playback state
        spotify_client = SpotifyClient(access_token=spotify_token)
        playback_state = spotify_client.get_playback_state()
        
        # Step 9: Start playback if not already playing
        playback_action = start_playback_if_needed(
            spotify_client=spotify_client,
            playback_state=playback_state,
            sensor=sensor,
            user=user
        )
        
        # Step 10: Update sensor state
        update_sensor_state(sensor_id, event_timestamp)
        
        # Step 11: Update session
        update_session(session_id, event_timestamp)
        
        # Step 12: Log motion event
        log_motion_event(
            sensor_id=sensor_id,
            user_id=user_id,
            session_id=session_id,
            timestamp=event_timestamp,
            action_taken=playback_action,
            metadata=metadata
        )
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log performance
        log_performance(
            logger,
            "motion_handler_complete",
            duration_ms,
            success=True,
            action=playback_action
        )
        
        # Return success response
        response = create_response(
            status_code=200,
            action=playback_action,
            message=f"Motion event processed: {playback_action}",
            sensor_id=sensor_id,
            session_id=session_id,
            duration_ms=round(duration_ms, 2)
        )
        
        logger.info("Motion event processed successfully", extra=response)
        
        return response
        
    except ValidationError as e:
        log_error(logger, e, "Validation error in motion handler")
        return create_error_response(e, "Validation failed")
        
    except ResourceNotFoundError as e:
        log_error(logger, e, "Resource not found")
        return create_error_response(e, "Resource not found")
        
    except SpotifyAPIError as e:
        log_error(logger, e, "Spotify API error")
        return create_error_response(e, "Spotify API error")
        
    except DynamoDBError as e:
        log_error(logger, e, "DynamoDB error")
        return create_error_response(e, "Database error")
        
    except Exception as e:
        log_error(logger, e, "Unexpected error in motion handler")
        return create_error_response(e, "Internal server error")


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def validate_environment():
    """Validate all required environment variables are set."""
    required_vars = [
        'SENSORS_TABLE',
        'USERS_TABLE',
        'SESSIONS_TABLE',
        'EVENTS_TABLE',
        'SPOTIFY_CREDENTIALS_SECRET'
    ]
    
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        raise ConfigurationError(
            message=f"Missing required environment variables: {', '.join(missing)}",
            details={"missing_variables": missing}
        )


def parse_event(event: Dict[str, Any]) -> Tuple[str, datetime, Dict[str, Any]]:
    """
    Parse and validate IoT Core event.
    
    Args:
        event: Raw IoT event
        
    Returns:
        Tuple of (sensor_id, timestamp, metadata)
        
    Raises:
        ValidationError: If event is invalid
    """
    sensor_id = event.get('sensorId')
    if not sensor_id:
        raise ValidationError(
            message="sensorId is required in event",
            field="sensorId"
        )
    
    # Parse timestamp
    timestamp_value = event.get('timestamp')
    if timestamp_value:
        if isinstance(timestamp_value, (int, float)):
            event_timestamp = datetime.fromtimestamp(timestamp_value)
        else:
            event_timestamp = datetime.fromisoformat(str(timestamp_value))
    else:
        event_timestamp = datetime.utcnow()
    
    # Extract metadata
    metadata = event.get('metadata', {})
    
    return sensor_id, event_timestamp, metadata


def get_sensor_config(sensor_id: str) -> Dict[str, Any]:
    """
    Retrieve sensor configuration from DynamoDB.
    
    Args:
        sensor_id: Sensor ID
        
    Returns:
        Sensor configuration dictionary
        
    Raises:
        ResourceNotFoundError: If sensor doesn't exist
    """
    logger.debug(f"Retrieving sensor configuration: {sensor_id}")
    
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    sensor = dynamodb.get_item({'sensorId': sensor_id})
    
    if not sensor:
        logger.error(f"Sensor not found: {sensor_id}")
        raise ResourceNotFoundError(
            message=f"Sensor not found: {sensor_id}",
            resource_type="Sensor",
            resource_id=sensor_id
        )
    
    logger.debug("Sensor configuration retrieved", extra={"sensor": sensor})
    return sensor


def get_user_config(user_id: str) -> Dict[str, Any]:
    """
    Retrieve user configuration from DynamoDB.
    
    Args:
        user_id: User ID
        
    Returns:
        User configuration dictionary
        
    Raises:
        ResourceNotFoundError: If user doesn't exist
    """
    logger.debug(f"Retrieving user configuration: {user_id}")
    
    dynamodb = DynamoDBHelper(USERS_TABLE)
    user = dynamodb.get_item({'userId': user_id})
    
    if not user:
        logger.error(f"User not found: {user_id}")
        raise ResourceNotFoundError(
            message=f"User not found: {user_id}",
            resource_type="User",
            resource_id=user_id
        )
    
    logger.debug("User configuration retrieved")
    return user


def is_quiet_hours(sensor: Dict[str, Any], event_time: datetime) -> bool:
    """
    Check if motion event occurred during quiet hours.
    
    Quiet hours prevent playback during specified times (e.g., 10PM-7AM).
    
    Args:
        sensor: Sensor configuration
        event_time: Time of motion event
        
    Returns:
        True if currently in quiet hours, False otherwise
    """
    quiet_hours = sensor.get('quiet_hours', {})
    
    if not quiet_hours.get('enabled', False):
        return False
    
    start_time_str = quiet_hours.get('start_time')
    end_time_str = quiet_hours.get('end_time')
    
    if not start_time_str or not end_time_str:
        logger.warning("Quiet hours enabled but times not configured")
        return False
    
    try:
        # Parse time strings (HH:MM format)
        start_hour, start_min = map(int, start_time_str.split(':'))
        end_hour, end_min = map(int, end_time_str.split(':'))
        
        start_time = dt_time(start_hour, start_min)
        end_time = dt_time(end_hour, end_min)
        current_time = event_time.time()
        
        # Handle quiet hours that span midnight
        if start_time < end_time:
            # Normal case: e.g., 22:00-07:00 -> check if 22:00 <= current < 07:00 next day
            in_quiet_hours = start_time <= current_time or current_time < end_time
        else:
            # Spans midnight: e.g., 22:00-02:00
            in_quiet_hours = start_time <= current_time or current_time < end_time
        
        if in_quiet_hours:
            logger.info(
                "Motion detected during quiet hours",
                extra={
                    "current_time": current_time.isoformat(),
                    "quiet_hours_start": start_time_str,
                    "quiet_hours_end": end_time_str
                }
            )
        
        return in_quiet_hours
        
    except (ValueError, AttributeError) as e:
        logger.error(f"Error parsing quiet hours: {e}", exc_info=True)
        return False


def should_debounce(sensor: Dict[str, Any], event_time: datetime) -> bool:
    """
    Check if motion event should be ignored due to debounce logic.
    
    Debounce prevents rapid repeated triggers by requiring a minimum time
    gap between motion events (e.g., 2 minutes).
    
    Args:
        sensor: Sensor configuration with lastMotionTime
        event_time: Time of current motion event
        
    Returns:
        True if event should be debounced (ignored), False otherwise
    """
    last_motion_time = sensor.get('lastMotionTime')
    
    if not last_motion_time:
        # No previous motion, allow this one
        return False
    
    try:
        # Parse last motion time
        if isinstance(last_motion_time, str):
            last_motion = datetime.fromisoformat(last_motion_time)
        elif isinstance(last_motion_time, datetime):
            last_motion = last_motion_time
        else:
            logger.warning(f"Invalid lastMotionTime format: {type(last_motion_time)}")
            return False
        
        # Get debounce period from sensor config
        debounce_minutes = sensor.get('preferences', {}).get('motionGapMinutes') or \
                          sensor.get('motion_debounce_minutes', MOTION_DEBOUNCE_DEFAULT_MINUTES)
        
        # Calculate time since last motion
        time_since_last = event_time - last_motion
        debounce_threshold = timedelta(minutes=debounce_minutes)
        
        if time_since_last < debounce_threshold:
            remaining_seconds = (debounce_threshold - time_since_last).total_seconds()
            logger.info(
                "Motion within debounce period",
                extra={
                    "time_since_last_seconds": time_since_last.total_seconds(),
                    "debounce_minutes": debounce_minutes,
                    "remaining_seconds": remaining_seconds
                }
            )
            return True
        
        return False
        
    except (ValueError, AttributeError) as e:
        logger.error(f"Error checking debounce: {e}", exc_info=True)
        return False


def get_or_create_session(sensor_id: str, user_id: str) -> Dict[str, Any]:
    """
    Get active session for sensor or create a new one.
    
    A session tracks a continuous period of bathroom usage. If there's
    already an active session for this sensor, we extend it. Otherwise,
    we create a new session.
    
    Args:
        sensor_id: Sensor ID
        user_id: User ID
        
    Returns:
        Session dictionary
    """
    logger.info("Getting or creating session")
    
    dynamodb = DynamoDBHelper(SESSIONS_TABLE)
    
    # Query for active session for this sensor
    # Using scan with filter for simplicity (can optimize with GSI later)
    try:
        from boto3.dynamodb.conditions import Attr
        
        response = dynamodb.table.scan(
            FilterExpression=Attr('sensorId').eq(sensor_id) & Attr('status').eq('active'),
            Limit=1
        )
        
        sessions = response.get('Items', [])
        
        if sessions:
            # Found active session, return it
            session = sessions[0]
            logger.info(
                "Found existing active session",
                extra={"session_id": session.get('sessionId')}
            )
            return session
        
    except Exception as e:
        logger.warning(f"Error querying for active session: {e}")
        # Continue to create new session
    
    # No active session found, create new one
    session_id = f"session-{sensor_id}-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    
    now = datetime.utcnow()
    ttl = int((now + timedelta(days=30)).timestamp())  # 30 days TTL
    
    session = {
        'sessionId': session_id,
        'sensorId': sensor_id,
        'userId': user_id,
        'status': 'active',
        'startTime': now.isoformat(),
        'lastMotionTime': now.isoformat(),
        'motionEventsCount': 1,
        'playbackStarted': False,
        'ttl': ttl
    }
    
    dynamodb.put_item(session)
    
    logger.info(
        "Created new session",
        extra={"session_id": session_id}
    )
    
    return session


def get_spotify_token(user: Dict[str, Any]) -> str:
    """
    Get Spotify access token for user from Secrets Manager.
    
    Args:
        user: User configuration
        
    Returns:
        Spotify access token
        
    Raises:
        SpotifyAuthenticationError: If token retrieval fails
    """
    token_secret_arn = user.get('spotify_token_secret_arn')
    
    if not token_secret_arn:
        raise SpotifyAuthenticationError(
            message="User has no Spotify token secret configured"
        )
    
    logger.debug("Retrieving Spotify access token from Secrets Manager")
    
    try:
        tokens = get_secret(token_secret_arn)
        access_token = tokens.get('access_token')
        
        if not access_token:
            raise SpotifyAuthenticationError(
                message="No access_token in user's Spotify secret"
            )
        
        logger.debug("Spotify access token retrieved successfully")
        return access_token
        
    except Exception as e:
        logger.error(f"Failed to retrieve Spotify token: {e}", exc_info=True)
        raise SpotifyAuthenticationError(
            message=f"Failed to retrieve Spotify access token: {str(e)}"
        )


def start_playback_if_needed(
    spotify_client: SpotifyClient,
    playback_state: Optional[Dict[str, Any]],
    sensor: Dict[str, Any],
    user: Dict[str, Any]
) -> str:
    """
    Start Spotify playback if not already playing.
    
    Args:
        spotify_client: Initialized Spotify client
        playback_state: Current playback state (or None)
        sensor: Sensor configuration
        user: User configuration
        
    Returns:
        Action taken: "playback_started", "already_playing", or "playback_resumed"
    """
    # Check if already playing
    if playback_state and playback_state.get('is_playing'):
        logger.info("Spotify already playing, no action needed")
        return "already_playing"
    
    # Get device ID and playlist from sensor or user config
    device_id = sensor.get('spotify_config', {}).get('device_id') or \
                sensor.get('spotifyDeviceId')
    
    playlist_uri = sensor.get('spotify_config', {}).get('playlist_uri') or \
                   sensor.get('playlistUri')
    
    if not device_id:
        logger.error("No Spotify device ID configured for sensor")
        raise ConfigurationError(
            message="Sensor has no Spotify device configured",
            config_key="spotify_config.device_id"
        )
    
    # Determine what to play
    context_uri = playlist_uri
    shuffle = sensor.get('spotify_config', {}).get('shuffle', True)
    volume = sensor.get('spotify_config', {}).get('volume_percent')
    
    logger.info(
        "Starting Spotify playback",
        extra={
            "device_id": device_id,
            "context_uri": context_uri,
            "shuffle": shuffle,
            "volume": volume
        }
    )
    
    # Start playback
    spotify_client.start_playback(
        device_id=device_id,
        context_uri=context_uri,
        shuffle=shuffle,
        volume_percent=volume
    )
    
    logger.info("Spotify playback started successfully")
    
    # Return appropriate action
    if playback_state and not playback_state.get('is_playing'):
        return "playback_resumed"
    else:
        return "playback_started"


def update_sensor_state(sensor_id: str, event_time: datetime):
    """
    Update sensor's lastMotionTime in DynamoDB.
    
    Args:
        sensor_id: Sensor ID
        event_time: Motion event timestamp
    """
    logger.debug("Updating sensor lastMotionTime")
    
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    dynamodb.update_item(
        key={'sensorId': sensor_id},
        updates={
            'lastMotionTime': event_time.isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'status': 'active'
        }
    )
    
    logger.debug("Sensor state updated")


def update_session(session_id: str, event_time: datetime):
    """
    Update session with new motion event.
    
    Args:
        session_id: Session ID
        event_time: Motion event timestamp
    """
    logger.debug("Updating session motion count")
    
    dynamodb = DynamoDBHelper(SESSIONS_TABLE)
    
    # Get current session to increment count
    session = dynamodb.get_item({'sessionId': session_id})
    current_count = session.get('motionEventsCount', 0) if session else 0
    
    # Update session
    dynamodb.update_item(
        key={'sessionId': session_id},
        updates={
            'lastMotionTime': event_time.isoformat(),
            'motionEventsCount': current_count + 1,
            'playbackStarted': True
        }
    )
    
    logger.debug("Session updated")


def log_motion_event(
    sensor_id: str,
    user_id: str,
    session_id: str,
    timestamp: datetime,
    action_taken: str,
    metadata: Dict[str, Any]
):
    """
    Log motion event to MotionEvents table for analytics.
    
    Args:
        sensor_id: Sensor ID
        user_id: User ID
        session_id: Session ID
        timestamp: Event timestamp
        action_taken: Action that was taken
        metadata: Event metadata
    """
    logger.debug("Logging motion event to MotionEvents table")
    
    event_id = f"event-{sensor_id}-{int(timestamp.timestamp())}-{uuid.uuid4().hex[:8]}"
    ttl = int((datetime.utcnow() + timedelta(days=30)).timestamp())
    
    motion_event = {
        'eventId': event_id,
        'sensorId': sensor_id,
        'userId': user_id,
        'sessionId': session_id,
        'eventType': 'motion_detected',
        'timestamp': timestamp.isoformat(),
        'actionTaken': action_taken,
        'playbackTriggered': action_taken in ['playback_started', 'playback_resumed'],
        'ttl': ttl
    }
    
    # Add metadata if present
    if metadata:
        if 'batteryLevel' in metadata:
            motion_event['batteryLevel'] = metadata['batteryLevel']
        if 'signalStrength' in metadata:
            motion_event['signalStrength'] = metadata['signalStrength']
        if 'firmwareVersion' in metadata:
            motion_event['firmwareVersion'] = metadata['firmwareVersion']
    
    dynamodb = DynamoDBHelper(EVENTS_TABLE)
    dynamodb.put_item(motion_event)
    
    logger.debug("Motion event logged", extra={"event_id": event_id})


# ==============================================================================
# RESPONSE HELPERS
# ==============================================================================

def create_response(
    status_code: int,
    action: str,
    message: str,
    sensor_id: str,
    session_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create standardized success response."""
    response = {
        'statusCode': status_code,
        'action': action,
        'sensorId': sensor_id,
        'message': message,
        **kwargs
    }
    
    if session_id:
        response['sessionId'] = session_id
    
    return response


def create_error_response(error: Exception, message: str) -> Dict[str, Any]:
    """Create standardized error response."""
    error_dict = {
        'statusCode': getattr(error, 'http_status', 500),
        'action': 'error',
        'error': type(error).__name__,
        'message': message,
        'details': str(error)
    }
    
    if hasattr(error, 'to_dict'):
        error_dict['error_details'] = error.to_dict()
    
    return error_dict
