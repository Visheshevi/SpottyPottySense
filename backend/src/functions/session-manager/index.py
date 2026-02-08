"""
Session Manager Lambda Function

Manages session lifecycle operations including creation, updates, completion,
and analytics queries. This function can be invoked directly via API Gateway
or internally by other Lambda functions for session management.

Operations:
- create_session: Create new session in DynamoDB
- update_session: Update session with motion events
- end_session: Mark session complete and calculate statistics
- get_active_session: Find active session for a sensor
- query_sessions: Query sessions by date range
- get_session_analytics: Calculate analytics for sessions

Environment Variables:
- SESSIONS_TABLE: DynamoDB Sessions table name
- EVENTS_TABLE: DynamoDB MotionEvents table name
- SESSION_TTL_DAYS: Days to retain sessions before auto-deletion
- LOG_LEVEL: Logging level

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2.5)
"""

import os
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from boto3.dynamodb.conditions import Key, Attr

from logger import get_logger, log_error, log_performance, add_persistent_context
from dynamodb_helper import DynamoDBHelper
from exceptions import (
    ValidationError,
    ResourceNotFoundError,
    DynamoDBError,
    ConfigurationError
)

logger = get_logger(__name__)

# Environment variables
SESSIONS_TABLE = os.environ.get('SESSIONS_TABLE')
EVENTS_TABLE = os.environ.get('EVENTS_TABLE')
SESSION_TTL_DAYS = int(os.environ.get('SESSION_TTL_DAYS', '30'))


def handler(event, context):
    """
    Lambda handler for session management operations.
    
    Args:
        event: Operation request with action and parameters
        context: Lambda context object
        
    Returns:
        dict: Result of the session operation
        
    Example Events:
        {
            "action": "create_session",
            "sensorId": "sensor-001",
            "userId": "user-001"
        }
        
        {
            "action": "get_active_session",
            "sensorId": "sensor-001"
        }
        
        {
            "action": "query_sessions",
            "sensorId": "sensor-001",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31"
        }
    """
    start_time = time.time()
    
    logger.info(
        "Session Manager invoked",
        extra={
            "function_name": context.function_name,
            "request_id": context.aws_request_id
        }
    )
    
    try:
        # Validate environment
        validate_environment()
        
        # Extract action
        action = event.get('action')
        if not action:
            raise ValidationError(
                message="action is required",
                field="action"
            )
        
        # Route to appropriate handler
        handlers = {
            'create_session': handle_create_session,
            'update_session': handle_update_session,
            'end_session': handle_end_session,
            'get_active_session': handle_get_active_session,
            'query_sessions': handle_query_sessions,
            'get_session_analytics': handle_get_session_analytics
        }
        
        handler_func = handlers.get(action)
        if not handler_func:
            raise ValidationError(
                message=f"Unknown action: {action}",
                field="action"
            )
        
        logger.info(f"Processing session action: {action}")
        
        # Execute handler
        result = handler_func(event)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log performance
        log_performance(
            logger,
            f"session_manager_{action}",
            duration_ms,
            success=True
        )
        
        # Add metadata to response
        result['duration_ms'] = round(duration_ms, 2)
        result['timestamp'] = datetime.utcnow().isoformat()
        
        logger.info("Session operation completed", extra=result)
        
        return result
        
    except ValidationError as e:
        log_error(logger, e, "Validation error in session manager")
        return {
            'statusCode': 400,
            'error': 'ValidationError',
            'message': str(e)
        }
        
    except ResourceNotFoundError as e:
        log_error(logger, e, "Resource not found")
        return {
            'statusCode': 404,
            'error': 'ResourceNotFoundError',
            'message': str(e)
        }
        
    except Exception as e:
        log_error(logger, e, "Unexpected error in session manager")
        return {
            'statusCode': 500,
            'error': 'InternalError',
            'message': str(e)
        }


# ==============================================================================
# OPERATION HANDLERS
# ==============================================================================

def handle_create_session(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new session.
    
    Args:
        event: Must contain sensorId and userId
        
    Returns:
        Response with created session details
    """
    sensor_id = event.get('sensorId')
    user_id = event.get('userId')
    
    if not sensor_id:
        raise ValidationError(message="sensorId is required", field="sensorId")
    if not user_id:
        raise ValidationError(message="userId is required", field="userId")
    
    add_persistent_context(logger, sensor_id=sensor_id, user_id=user_id)
    
    # Generate session ID
    session_id = f"session-{sensor_id}-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    
    # Create session object
    now = datetime.utcnow()
    now_timestamp = int(now.timestamp())
    ttl = int((now + timedelta(days=SESSION_TTL_DAYS)).timestamp())
    
    session = {
        'sessionId': session_id,
        'sensorId': sensor_id,
        'userId': user_id,
        'status': 'active',
        'startTime': now_timestamp,  # Unix timestamp for GSI
        'startTimeISO': now.isoformat(),  # ISO format for readability
        'lastMotionTime': now.isoformat(),
        'motionEventsCount': 1,
        'playbackStarted': False,
        'createdAt': now.isoformat(),
        'updatedAt': now.isoformat(),
        'ttl': ttl
    }
    
    # Optional fields from event
    if 'spotifyDeviceId' in event:
        session['spotifyDeviceId'] = event['spotifyDeviceId']
    if 'spotifyContextUri' in event:
        session['spotifyContextUri'] = event['spotifyContextUri']
    
    # Save to DynamoDB
    dynamodb = DynamoDBHelper(SESSIONS_TABLE)
    dynamodb.put_item(session)
    
    logger.info(
        "Session created",
        extra={"session_id": session_id, "sensor_id": sensor_id}
    )
    
    return {
        'statusCode': 200,
        'action': 'create_session',
        'session': session
    }


def handle_update_session(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing session.
    
    Args:
        event: Must contain sessionId and updates
        
    Returns:
        Response with updated session
    """
    session_id = event.get('sessionId')
    if not session_id:
        raise ValidationError(message="sessionId is required", field="sessionId")
    
    add_persistent_context(logger, session_id=session_id)
    
    # Get current session
    dynamodb = DynamoDBHelper(SESSIONS_TABLE)
    session = dynamodb.get_item({'sessionId': session_id})
    
    if not session:
        raise ResourceNotFoundError(
            message=f"Session not found: {session_id}",
            resource_type="Session",
            resource_id=session_id
        )
    
    # Build updates
    updates = {
        'updatedAt': datetime.utcnow().isoformat()
    }
    
    # Update motion count
    if event.get('incrementMotionCount'):
        current_count = session.get('motionEventsCount', 0)
        updates['motionEventsCount'] = current_count + 1
        updates['lastMotionTime'] = datetime.utcnow().isoformat()
    
    # Update playback status
    if 'playbackStarted' in event:
        updates['playbackStarted'] = event['playbackStarted']
    
    # Update Spotify context
    if 'spotifyDeviceId' in event:
        updates['spotifyDeviceId'] = event['spotifyDeviceId']
    if 'spotifyContextUri' in event:
        updates['spotifyContextUri'] = event['spotifyContextUri']
    
    # Apply updates
    dynamodb.update_item(
        key={'sessionId': session_id},
        updates=updates
    )
    
    # Get updated session
    updated_session = dynamodb.get_item({'sessionId': session_id})
    
    logger.info("Session updated", extra={"session_id": session_id})
    
    return {
        'statusCode': 200,
        'action': 'update_session',
        'session': updated_session
    }


def handle_end_session(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    End a session and calculate statistics.
    
    Args:
        event: Must contain sessionId
        
    Returns:
        Response with completed session
    """
    session_id = event.get('sessionId')
    if not session_id:
        raise ValidationError(message="sessionId is required", field="sessionId")
    
    add_persistent_context(logger, session_id=session_id)
    
    # Get current session
    dynamodb = DynamoDBHelper(SESSIONS_TABLE)
    session = dynamodb.get_item({'sessionId': session_id})
    
    if not session:
        raise ResourceNotFoundError(
            message=f"Session not found: {session_id}",
            resource_type="Session",
            resource_id=session_id
        )
    
    # Calculate duration
    start_time = parse_datetime(session.get('startTime'))
    end_time = datetime.utcnow()
    
    duration_minutes = None
    if start_time:
        duration = end_time - start_time
        duration_minutes = round(duration.total_seconds() / 60, 2)
    
    # Update session
    updates = {
        'status': 'completed',
        'endTime': end_time.isoformat(),
        'durationMinutes': duration_minutes,
        'updatedAt': end_time.isoformat()
    }
    
    # Add playback stopped flag if provided
    if 'playbackStopped' in event:
        updates['playbackStopped'] = event['playbackStopped']
    
    dynamodb.update_item(
        key={'sessionId': session_id},
        updates=updates
    )
    
    # Get completed session
    completed_session = dynamodb.get_item({'sessionId': session_id})
    
    logger.info(
        "Session ended",
        extra={
            "session_id": session_id,
            "duration_minutes": duration_minutes
        }
    )
    
    return {
        'statusCode': 200,
        'action': 'end_session',
        'session': completed_session
    }


def handle_get_active_session(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get active session for a sensor.
    
    Args:
        event: Must contain sensorId
        
    Returns:
        Response with active session or None
    """
    sensor_id = event.get('sensorId')
    if not sensor_id:
        raise ValidationError(message="sensorId is required", field="sensorId")
    
    add_persistent_context(logger, sensor_id=sensor_id)
    
    # Query active sessions for this sensor
    dynamodb = DynamoDBHelper(SESSIONS_TABLE)
    
    # Scan for active sessions (can be optimized with GSI later)
    response = dynamodb.table.scan(
        FilterExpression=Attr('sensorId').eq(sensor_id) & Attr('status').eq('active'),
        Limit=1
    )
    
    sessions = response.get('Items', [])
    
    if sessions:
        session = sessions[0]
        logger.info(
            "Found active session",
            extra={"session_id": session.get('sessionId')}
        )
        return {
            'statusCode': 200,
            'action': 'get_active_session',
            'session': session
        }
    else:
        logger.info("No active session found")
        return {
            'statusCode': 200,
            'action': 'get_active_session',
            'session': None
        }


def handle_query_sessions(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query sessions by sensor and date range.
    
    Args:
        event: Must contain sensorId, optionally startDate and endDate
        
    Returns:
        Response with list of sessions
    """
    sensor_id = event.get('sensorId')
    if not sensor_id:
        raise ValidationError(message="sensorId is required", field="sensorId")
    
    start_date = event.get('startDate')
    end_date = event.get('endDate')
    limit = event.get('limit', 100)
    
    add_persistent_context(logger, sensor_id=sensor_id)
    
    # Query sessions using SensorIdIndex GSI
    dynamodb = DynamoDBHelper(SESSIONS_TABLE)
    
    # Build filter expression
    filter_parts = []
    expr_values = {'sid': sensor_id}
    
    if start_date:
        start_timestamp = parse_datetime(start_date)
        if start_timestamp:
            expr_values['start'] = int(start_timestamp.timestamp())
            filter_parts.append('startTime >= :start')
    
    if end_date:
        end_timestamp = parse_datetime(end_date)
        if end_timestamp:
            expr_values['end'] = int(end_timestamp.timestamp())
            filter_parts.append('startTime <= :end')
    
    # Query
    key_condition = 'sensorId = :sid'
    filter_expression = ' AND '.join(filter_parts) if filter_parts else None
    
    response = dynamodb.query(
        key_condition=key_condition,
        filter_expression=filter_expression,
        index_name='SensorIdIndex',
        limit=limit,
        scan_forward=False,  # Most recent first
        **expr_values
    )
    
    sessions = response.get('Items', [])
    
    logger.info(
        "Sessions queried",
        extra={
            "sensor_id": sensor_id,
            "session_count": len(sessions),
            "has_more": 'LastEvaluatedKey' in response
        }
    )
    
    return {
        'statusCode': 200,
        'action': 'query_sessions',
        'sessions': sessions,
        'count': len(sessions),
        'hasMore': 'LastEvaluatedKey' in response,
        'lastEvaluatedKey': response.get('LastEvaluatedKey')
    }


def handle_get_session_analytics(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate analytics for sessions.
    
    Args:
        event: Must contain sensorId or userId, optionally startDate and endDate
        
    Returns:
        Response with analytics data
    """
    sensor_id = event.get('sensorId')
    user_id = event.get('userId')
    
    if not sensor_id and not user_id:
        raise ValidationError(
            message="sensorId or userId is required",
            field="sensorId/userId"
        )
    
    start_date = event.get('startDate')
    end_date = event.get('endDate')
    
    # Query sessions
    query_event = {'limit': 1000}
    if sensor_id:
        query_event['sensorId'] = sensor_id
        add_persistent_context(logger, sensor_id=sensor_id)
    
    if start_date:
        query_event['startDate'] = start_date
    if end_date:
        query_event['endDate'] = end_date
    
    # Get sessions
    if sensor_id:
        sessions_response = handle_query_sessions(query_event)
        sessions = sessions_response.get('sessions', [])
    else:
        # Query by userId (scan with filter)
        dynamodb = DynamoDBHelper(SESSIONS_TABLE)
        response = dynamodb.table.scan(
            FilterExpression=Attr('userId').eq(user_id),
            Limit=1000
        )
        sessions = response.get('Items', [])
    
    # Calculate analytics
    analytics = calculate_analytics(sessions)
    
    logger.info(
        "Session analytics calculated",
        extra={"total_sessions": analytics['totalSessions']}
    )
    
    return {
        'statusCode': 200,
        'action': 'get_session_analytics',
        'analytics': analytics
    }


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def validate_environment() -> None:
    """Validate required environment variables."""
    required = ['SESSIONS_TABLE', 'EVENTS_TABLE']
    missing = [var for var in required if not os.environ.get(var)]
    
    if missing:
        raise ConfigurationError(
            message=f"Missing required environment variables: {', '.join(missing)}",
            details={"missing_variables": missing}
        )


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


def calculate_analytics(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate analytics from a list of sessions.
    
    Args:
        sessions: List of session dictionaries
        
    Returns:
        Dictionary with analytics data
    """
    if not sessions:
        return {
            'totalSessions': 0,
            'activeSessions': 0,
            'completedSessions': 0,
            'totalMotionEvents': 0,
            'totalDurationMinutes': 0,
            'averageDurationMinutes': 0,
            'averageMotionEventsPerSession': 0
        }
    
    total_sessions = len(sessions)
    active_sessions = sum(1 for s in sessions if s.get('status') == 'active')
    completed_sessions = sum(1 for s in sessions if s.get('status') == 'completed')
    
    total_motion_events = sum(s.get('motionEventsCount', 0) for s in sessions)
    
    # Calculate duration stats (only for completed sessions)
    completed_with_duration = [
        s for s in sessions
        if s.get('status') == 'completed' and s.get('durationMinutes')
    ]
    
    total_duration = sum(s.get('durationMinutes', 0) for s in completed_with_duration)
    avg_duration = total_duration / len(completed_with_duration) if completed_with_duration else 0
    
    avg_motion_events = total_motion_events / total_sessions if total_sessions else 0
    
    # Find most common times
    session_hours = [
        parse_datetime(s.get('startTime')).hour
        for s in sessions
        if parse_datetime(s.get('startTime'))
    ]
    
    peak_hour = max(set(session_hours), key=session_hours.count) if session_hours else None
    
    return {
        'totalSessions': total_sessions,
        'activeSessions': active_sessions,
        'completedSessions': completed_sessions,
        'totalMotionEvents': total_motion_events,
        'totalDurationMinutes': round(total_duration, 2),
        'averageDurationMinutes': round(avg_duration, 2),
        'averageMotionEventsPerSession': round(avg_motion_events, 2),
        'peakHour': peak_hour,
        'sessionsWithPlayback': sum(1 for s in sessions if s.get('playbackStarted'))
    }
