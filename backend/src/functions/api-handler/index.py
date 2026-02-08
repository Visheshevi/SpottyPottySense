"""
API Handler Function

REST API backend for dashboard - handles all CRUD operations for sensors, users,
sessions, and analytics.

Endpoints:
- GET /sensors - List user's sensors
- POST /sensors - Register new sensor
- GET /sensors/{id} - Get sensor details
- PUT /sensors/{id} - Update sensor configuration
- DELETE /sensors/{id} - Soft delete sensor
- GET /users/me - Get user profile
- PUT /users/me - Update user preferences
- GET /spotify/devices - List Spotify devices
- POST /spotify/test - Test Spotify playback
- GET /sessions - Query sessions with filters
- GET /analytics - Get aggregated statistics
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal

# AWS Lambda Powertools
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

# Import shared utilities from Lambda Layer
from dynamodb_helper import DynamoDBHelper
from spotify_client import SpotifyClient
from secrets_helper import SecretsHelper
from validation import (
    Sensor, User, Session, MotionEvent,
    ValidationError, ResourceNotFoundError, AuthorizationError
)
from logger import get_logger, add_persistent_context, log_error, log_performance
from exceptions import SpotifyAPIError, DynamoDBError

# Initialize logger
logger = get_logger(__name__)

# Environment variables
SENSORS_TABLE = os.environ.get('SENSORS_TABLE')
USERS_TABLE = os.environ.get('USERS_TABLE')
SESSIONS_TABLE = os.environ.get('SESSIONS_TABLE')
MOTION_EVENTS_TABLE = os.environ.get('MOTION_EVENTS_TABLE')
SPOTIFY_SECRET_NAME = os.environ.get('SPOTIFY_SECRET_NAME')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')

# Constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ==============================================================================
# MAIN HANDLER
# ==============================================================================

def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for API Gateway requests.
    Handles all REST API endpoints for the dashboard.
    
    Args:
        event: API Gateway event with HTTP method, path, body, etc.
        context: Lambda context object
        
    Returns:
        dict: API Gateway response with status code, headers, and body
    """
    start_time = time.time()
    
    logger.info(
        "API Handler invoked",
        extra={
            "function_name": context.function_name,
            "request_id": context.aws_request_id,
            "http_method": event.get('httpMethod'),
            "path": event.get('path')
        }
    )
    
    try:
        # Validate environment
        validate_environment()
        
        # Extract request information
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        body = parse_body(event.get('body'))
        
        # Extract and validate user from Cognito authorizer
        user_id = extract_user_id(event)
        add_persistent_context(logger, user_id=user_id)
        
        logger.info(f"Processing {http_method} {path} for user {user_id}")
        
        # Route to appropriate handler
        response_data = route_request(
            http_method, path, path_parameters, query_parameters, body, user_id
        )
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log performance
        log_performance(
            logger,
            f"api_{http_method.lower()}_{path.replace('/', '_')}",
            duration_ms,
            success=True
        )
        
        return create_response(200, response_data)
        
    except ValidationError as e:
        log_error(logger, e, "Validation error")
        return create_response(400, {
            'error': 'ValidationError',
            'message': str(e),
            'field': getattr(e, 'field', None)
        })
        
    except ResourceNotFoundError as e:
        log_error(logger, e, "Resource not found")
        return create_response(404, {
            'error': 'ResourceNotFoundError',
            'message': str(e)
        })
        
    except AuthorizationError as e:
        log_error(logger, e, "Authorization error")
        return create_response(403, {
            'error': 'AuthorizationError',
            'message': str(e)
        })
        
    except Exception as e:
        log_error(logger, e, "Unexpected error in API handler")
        return create_response(500, {
            'error': 'InternalError',
            'message': 'An internal error occurred'
        })


# ==============================================================================
# ROUTING
# ==============================================================================

def route_request(
    method: str,
    path: str,
    path_params: Dict[str, Any],
    query_params: Dict[str, Any],
    body: Optional[Dict[str, Any]],
    user_id: str
) -> Dict[str, Any]:
    """
    Route request to appropriate handler based on path and method.
    
    Args:
        method: HTTP method
        path: Request path
        path_params: Path parameters
        query_params: Query string parameters
        body: Request body
        user_id: Authenticated user ID
        
    Returns:
        Response data dictionary
        
    Raises:
        ValidationError: If endpoint not found
    """
    # Sensor endpoints
    if path == '/sensors':
        if method == 'GET':
            return handle_list_sensors(user_id, query_params)
        elif method == 'POST':
            return handle_create_sensor(user_id, body)
    
    elif path.startswith('/sensors/'):
        sensor_id = path_params.get('id')
        if not sensor_id:
            raise ValidationError(message="Sensor ID is required", field="id")
        
        if method == 'GET':
            return handle_get_sensor(user_id, sensor_id)
        elif method == 'PUT':
            return handle_update_sensor(user_id, sensor_id, body)
        elif method == 'DELETE':
            return handle_delete_sensor(user_id, sensor_id)
    
    # User endpoints
    elif path == '/users/me':
        if method == 'GET':
            return handle_get_user(user_id)
        elif method == 'PUT':
            return handle_update_user(user_id, body)
    
    # Spotify endpoints
    elif path == '/spotify/devices':
        if method == 'GET':
            return handle_get_spotify_devices(user_id)
    
    elif path == '/spotify/test':
        if method == 'POST':
            return handle_test_spotify(user_id, body)
    
    # Analytics endpoints
    elif path == '/sessions':
        if method == 'GET':
            return handle_get_sessions(user_id, query_params)
    
    elif path == '/analytics':
        if method == 'GET':
            return handle_get_analytics(user_id, query_params)
    
    # Unknown endpoint
    raise ValidationError(
        message=f"Endpoint not found: {method} {path}",
        field="path"
    )


# ==============================================================================
# SENSOR ENDPOINTS
# ==============================================================================

def handle_list_sensors(user_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List all sensors for the authenticated user.
    
    Query Parameters:
    - limit: Page size (default 20, max 100)
    - lastKey: Pagination token
    - includeDeleted: Include soft-deleted sensors (default false)
    
    Returns:
        List of sensors with pagination info
    """
    logger.info(f"Listing sensors for user: {user_id}")
    
    # Parse pagination parameters
    limit = int(query_params.get('limit', DEFAULT_PAGE_SIZE))
    limit = min(limit, MAX_PAGE_SIZE)
    last_key = query_params.get('lastKey')
    include_deleted = query_params.get('includeDeleted', 'false').lower() == 'true'
    
    # Query sensors table
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    
    # Use GSI to query by userId
    response = dynamodb.query(
        key_condition="userId = :userId",
        index_name="UserIdIndex",
        limit=limit,
        exclusive_start_key=json.loads(last_key) if last_key else None,
        userId=user_id
    )
    sensors = response.get('Items', [])
    
    # Filter out deleted sensors if requested
    if not include_deleted:
        sensors = [s for s in sensors if not s.get('isDeleted', False)]
    
    # Convert Decimals to floats for JSON serialization
    sensors = convert_decimals(sensors)
    
    result = {
        'sensors': sensors,
        'count': len(sensors),
        'limit': limit
    }
    
    # Add pagination token if more results exist
    if 'LastEvaluatedKey' in response:
        result['nextToken'] = json.dumps(response['LastEvaluatedKey'])
    
    logger.info(f"Found {len(sensors)} sensors for user")
    return result


def handle_create_sensor(user_id: str, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Register a new sensor by invoking the device registration function.
    
    This endpoint delegates to the DeviceRegistration Lambda function.
    
    Body Parameters:
    - sensorId: Unique sensor identifier (required)
    - location: Physical location (required)
    - name: Friendly name (optional)
    - spotifyDeviceId: Spotify device ID (optional)
    - playlistUri: Spotify playlist URI (optional)
    - timeoutMinutes: Inactivity timeout (optional)
    - motionDebounceMinutes: Motion debounce time (optional)
    
    Returns:
        Registration result with certificates (ONE TIME ONLY)
    """
    if not body:
        raise ValidationError(message="Request body is required", field="body")
    
    logger.info(f"Creating sensor for user: {user_id}")
    
    # Validate required fields
    sensor_id = body.get('sensorId')
    location = body.get('location')
    
    if not sensor_id:
        raise ValidationError(message="sensorId is required", field="sensorId")
    if not location:
        raise ValidationError(message="location is required", field="location")
    
    # Add userId to body
    body['userId'] = user_id
    body['action'] = 'register'
    
    # Invoke device registration function
    import boto3
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    
    function_name = os.environ.get('DEVICE_REGISTRATION_FUNCTION_NAME')
    
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(body)
    )
    
    result = json.loads(response['Payload'].read())
    
    # Check if invocation was successful
    if result.get('statusCode') != 200:
        error_body = json.loads(result.get('body', '{}'))
        raise ValidationError(
            message=error_body.get('message', 'Failed to register sensor'),
            field='sensorId'
        )
    
    # Parse response
    if isinstance(result.get('body'), str):
        registration_result = json.loads(result['body'])
    else:
        registration_result = result
    
    logger.info(f"Sensor created successfully: {sensor_id}")
    return registration_result


def handle_get_sensor(user_id: str, sensor_id: str) -> Dict[str, Any]:
    """
    Get details for a specific sensor.
    
    Args:
        user_id: Authenticated user ID
        sensor_id: Sensor ID to retrieve
        
    Returns:
        Sensor details
    """
    logger.info(f"Getting sensor: {sensor_id} for user: {user_id}")
    
    # Get sensor from DynamoDB
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    sensor = dynamodb.get_item({'sensorId': sensor_id})
    
    if not sensor:
        raise ResourceNotFoundError(
            message=f"Sensor not found: {sensor_id}",
            resource_type="Sensor",
            resource_id=sensor_id
        )
    
    # Verify user owns this sensor
    if sensor.get('userId') != user_id:
        raise AuthorizationError(
            message="You do not have permission to access this sensor"
        )
    
    # Convert Decimals to floats
    sensor = convert_decimals(sensor)
    
    logger.info(f"Sensor retrieved: {sensor_id}")
    return {'sensor': sensor}


def handle_update_sensor(
    user_id: str,
    sensor_id: str,
    body: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Update sensor configuration.
    
    Updatable fields:
    - name: Friendly name
    - location: Physical location
    - spotifyDeviceId: Spotify device ID
    - playlistUri: Spotify playlist URI
    - timeoutMinutes: Inactivity timeout
    - motionDebounceMinutes: Motion debounce time
    - quietHours: Quiet hours configuration
    - isActive: Enable/disable sensor
    
    Args:
        user_id: Authenticated user ID
        sensor_id: Sensor ID to update
        body: Update fields
        
    Returns:
        Updated sensor details
    """
    if not body:
        raise ValidationError(message="Request body is required", field="body")
    
    logger.info(f"Updating sensor: {sensor_id} for user: {user_id}")
    
    # Get existing sensor
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    sensor = dynamodb.get_item({'sensorId': sensor_id})
    
    if not sensor:
        raise ResourceNotFoundError(
            message=f"Sensor not found: {sensor_id}",
            resource_type="Sensor",
            resource_id=sensor_id
        )
    
    # Verify user owns this sensor
    if sensor.get('userId') != user_id:
        raise AuthorizationError(
            message="You do not have permission to update this sensor"
        )
    
    # Build update expression
    updatable_fields = [
        'name', 'location', 'spotifyDeviceId', 'playlistUri',
        'timeoutMinutes', 'motionDebounceMinutes', 'quietHours', 'isActive'
    ]
    
    update_parts = []
    attribute_values = {}
    
    for field in updatable_fields:
        if field in body:
            update_parts.append(f"{field} = :{field}")
            attribute_values[f":{field}"] = body[field]
    
    if not update_parts:
        raise ValidationError(
            message="No updatable fields provided",
            field="body"
        )
    
    # Add updatedAt timestamp
    update_parts.append("updatedAt = :updatedAt")
    attribute_values[':updatedAt'] = datetime.utcnow().isoformat()
    
    # Perform update
    updated_sensor = dynamodb.update_item(
        key={'sensorId': sensor_id},
        update_expression=f"SET {', '.join(update_parts)}",
        expression_attribute_values=attribute_values,
        return_values='ALL_NEW'
    )
    
    # Convert Decimals to floats
    updated_sensor = convert_decimals(updated_sensor)
    
    logger.info(f"Sensor updated: {sensor_id}")
    return {
        'sensor': updated_sensor,
        'message': f'Sensor {sensor_id} updated successfully'
    }


def handle_delete_sensor(user_id: str, sensor_id: str) -> Dict[str, Any]:
    """
    Soft delete a sensor (mark as deleted but keep in database).
    
    To permanently delete, use the device deregistration endpoint.
    
    Args:
        user_id: Authenticated user ID
        sensor_id: Sensor ID to delete
        
    Returns:
        Deletion confirmation
    """
    logger.info(f"Deleting sensor: {sensor_id} for user: {user_id}")
    
    # Get existing sensor
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    sensor = dynamodb.get_item({'sensorId': sensor_id})
    
    if not sensor:
        raise ResourceNotFoundError(
            message=f"Sensor not found: {sensor_id}",
            resource_type="Sensor",
            resource_id=sensor_id
        )
    
    # Verify user owns this sensor
    if sensor.get('userId') != user_id:
        raise AuthorizationError(
            message="You do not have permission to delete this sensor"
        )
    
    # Soft delete (mark as deleted)
    dynamodb.update_item(
        key={'sensorId': sensor_id},
        update_expression="SET isDeleted = :true, deletedAt = :deletedAt, isActive = :false",
        expression_attribute_values={
            ':true': True,
            ':false': False,
            ':deletedAt': datetime.utcnow().isoformat()
        }
    )
    
    logger.info(f"Sensor soft deleted: {sensor_id}")
    return {
        'sensorId': sensor_id,
        'message': f'Sensor {sensor_id} deleted successfully',
        'note': 'This is a soft delete. To permanently remove, use the deregistration endpoint.'
    }


# ==============================================================================
# USER ENDPOINTS
# ==============================================================================

def handle_get_user(user_id: str) -> Dict[str, Any]:
    """
    Get user profile and preferences.
    
    Args:
        user_id: Authenticated user ID
        
    Returns:
        User profile
    """
    logger.info(f"Getting user profile: {user_id}")
    
    # Get user from DynamoDB
    dynamodb = DynamoDBHelper(USERS_TABLE)
    user = dynamodb.get_item({'userId': user_id})
    
    if not user:
        raise ResourceNotFoundError(
            message=f"User not found: {user_id}",
            resource_type="User",
            resource_id=user_id
        )
    
    # Remove sensitive fields
    user.pop('spotifyRefreshToken', None)
    
    # Convert Decimals to floats
    user = convert_decimals(user)
    
    logger.info(f"User profile retrieved: {user_id}")
    return {'user': user}


def handle_update_user(user_id: str, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Update user preferences.
    
    Updatable fields:
    - email: Email address
    - name: Display name
    - spotifyAccessToken: Spotify access token
    - spotifyRefreshToken: Spotify refresh token
    - spotifyTokenExpiry: Token expiry timestamp
    - defaultSpotifyDeviceId: Default playback device
    - defaultPlaylistUri: Default playlist
    - notificationsEnabled: Enable notifications
    
    Args:
        user_id: Authenticated user ID
        body: Update fields
        
    Returns:
        Updated user profile
    """
    if not body:
        raise ValidationError(message="Request body is required", field="body")
    
    logger.info(f"Updating user profile: {user_id}")
    
    # Get existing user
    dynamodb = DynamoDBHelper(USERS_TABLE)
    user = dynamodb.get_item({'userId': user_id})
    
    if not user:
        raise ResourceNotFoundError(
            message=f"User not found: {user_id}",
            resource_type="User",
            resource_id=user_id
        )
    
    # Build update expression
    updatable_fields = [
        'email', 'name', 'spotifyAccessToken', 'spotifyRefreshToken',
        'spotifyTokenExpiry', 'defaultSpotifyDeviceId', 'defaultPlaylistUri',
        'notificationsEnabled'
    ]
    
    update_parts = []
    attribute_values = {}
    
    for field in updatable_fields:
        if field in body:
            update_parts.append(f"{field} = :{field}")
            attribute_values[f":{field}"] = body[field]
    
    if not update_parts:
        raise ValidationError(
            message="No updatable fields provided",
            field="body"
        )
    
    # Add updatedAt timestamp
    update_parts.append("updatedAt = :updatedAt")
    attribute_values[':updatedAt'] = datetime.utcnow().isoformat()
    
    # Perform update
    updated_user = dynamodb.update_item(
        key={'userId': user_id},
        update_expression=f"SET {', '.join(update_parts)}",
        expression_attribute_values=attribute_values,
        return_values='ALL_NEW'
    )
    
    # Remove sensitive fields
    updated_user.pop('spotifyRefreshToken', None)
    
    # Convert Decimals to floats
    updated_user = convert_decimals(updated_user)
    
    logger.info(f"User profile updated: {user_id}")
    return {
        'user': updated_user,
        'message': 'User profile updated successfully'
    }


# ==============================================================================
# SPOTIFY ENDPOINTS
# ==============================================================================

def handle_get_spotify_devices(user_id: str) -> Dict[str, Any]:
    """
    List available Spotify devices for the user.
    
    Args:
        user_id: Authenticated user ID
        
    Returns:
        List of Spotify devices
    """
    logger.info(f"Getting Spotify devices for user: {user_id}")
    
    # Get user's Spotify token
    access_token = get_spotify_access_token(user_id)
    
    # Initialize Spotify client
    spotify = SpotifyClient(access_token=access_token)
    
    try:
        # Get devices from Spotify API
        devices = spotify.get_devices()
        
        logger.info(f"Found {len(devices)} Spotify devices")
        return {
            'devices': devices,
            'count': len(devices)
        }
        
    except SpotifyAPIError as e:
        logger.error(f"Failed to get Spotify devices: {e}")
        raise ValidationError(
            message="Failed to retrieve Spotify devices. Please check your Spotify account.",
            field="spotify"
        )


def handle_test_spotify(user_id: str, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Test Spotify playback with specified device and playlist.
    
    Body Parameters:
    - deviceId: Spotify device ID (required)
    - playlistUri: Playlist URI (optional, uses user's default if not provided)
    - action: 'play' or 'pause' (default: 'play')
    
    Args:
        user_id: Authenticated user ID
        body: Test parameters
        
    Returns:
        Test result
    """
    if not body:
        raise ValidationError(message="Request body is required", field="body")
    
    device_id = body.get('deviceId')
    playlist_uri = body.get('playlistUri')
    action = body.get('action', 'play')
    
    if not device_id:
        raise ValidationError(message="deviceId is required", field="deviceId")
    
    logger.info(f"Testing Spotify {action} for user: {user_id}")
    
    # Get user's configuration
    dynamodb = DynamoDBHelper(USERS_TABLE)
    user = dynamodb.get_item({'userId': user_id})
    
    if not user:
        raise ResourceNotFoundError(
            message=f"User not found: {user_id}",
            resource_type="User",
            resource_id=user_id
        )
    
    # Use default playlist if not provided
    if not playlist_uri:
        playlist_uri = user.get('defaultPlaylistUri')
    
    # Get Spotify access token
    access_token = get_spotify_access_token(user_id)
    
    # Initialize Spotify client
    spotify = SpotifyClient(access_token=access_token)
    
    try:
        if action == 'play':
            # Start playback
            spotify.start_playback(
                device_id=device_id,
                context_uri=playlist_uri
            )
            message = 'Playback started successfully'
        elif action == 'pause':
            # Pause playback
            spotify.pause_playback(device_id=device_id)
            message = 'Playback paused successfully'
        else:
            raise ValidationError(
                message=f"Invalid action: {action}. Must be 'play' or 'pause'",
                field="action"
            )
        
        logger.info(f"Spotify test {action} completed")
        return {
            'success': True,
            'action': action,
            'deviceId': device_id,
            'playlistUri': playlist_uri,
            'message': message
        }
        
    except SpotifyAPIError as e:
        logger.error(f"Spotify test failed: {e}")
        raise ValidationError(
            message=f"Spotify test failed: {str(e)}",
            field="spotify"
        )


# ==============================================================================
# ANALYTICS ENDPOINTS
# ==============================================================================

def handle_get_sessions(user_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query sessions with filters.
    
    Query Parameters:
    - sensorId: Filter by sensor ID (optional)
    - startDate: Filter start date (ISO format, optional)
    - endDate: Filter end date (ISO format, optional)
    - status: Filter by status ('active', 'completed', optional)
    - limit: Page size (default 20, max 100)
    - lastKey: Pagination token
    
    Args:
        user_id: Authenticated user ID
        query_params: Query parameters
        
    Returns:
        List of sessions with pagination
    """
    logger.info(f"Querying sessions for user: {user_id}")
    
    # Parse parameters
    sensor_id = query_params.get('sensorId')
    start_date = query_params.get('startDate')
    end_date = query_params.get('endDate')
    status = query_params.get('status')
    limit = int(query_params.get('limit', DEFAULT_PAGE_SIZE))
    limit = min(limit, MAX_PAGE_SIZE)
    last_key = query_params.get('lastKey')
    
    # Get user's sensors to verify ownership
    sensors_db = DynamoDBHelper(SENSORS_TABLE)
    user_sensors_response = sensors_db.query(
        key_condition="userId = :userId",
        index_name="UserIdIndex",
        userId=user_id
    )
    user_sensor_ids = {s['sensorId'] for s in user_sensors_response.get('Items', [])}
    
    # Query sessions
    sessions_db = DynamoDBHelper(SESSIONS_TABLE)
    
    if sensor_id:
        # Verify user owns this sensor
        if sensor_id not in user_sensor_ids:
            raise AuthorizationError(
                message="You do not have permission to access sessions for this sensor"
            )
        
        # Query by sensorId using GSI
        response = sessions_db.query(
            key_condition="sensorId = :sensorId",
            index_name="SensorIdIndex",
            limit=limit,
            scan_forward=False,  # Most recent first
            exclusive_start_key=json.loads(last_key) if last_key else None,
            sensorId=sensor_id
        )
    else:
        # Scan all sessions (less efficient, but necessary without sensorId)
        # In production, consider adding a userId GSI
        scan_params = {
            'Limit': limit * 5  # Overscan to account for filtering
        }
        
        if last_key:
            scan_params['ExclusiveStartKey'] = json.loads(last_key)
        
        response = sessions_db.scan(**scan_params)
        
        # Filter to user's sensors only
        all_sessions = response.get('Items', [])
        response['Items'] = [
            s for s in all_sessions
            if s.get('sensorId') in user_sensor_ids
        ]
    
    sessions = response.get('Items', [])
    
    # Apply additional filters
    if status:
        sessions = [s for s in sessions if s.get('status') == status]
    
    if start_date:
        start_timestamp = int(datetime.fromisoformat(start_date.replace('Z', '+00:00')).timestamp())
        sessions = [s for s in sessions if s.get('startTime', 0) >= start_timestamp]
    
    if end_date:
        end_timestamp = int(datetime.fromisoformat(end_date.replace('Z', '+00:00')).timestamp())
        sessions = [s for s in sessions if s.get('startTime', 0) <= end_timestamp]
    
    # Limit results
    sessions = sessions[:limit]
    
    # Convert Decimals to floats
    sessions = convert_decimals(sessions)
    
    result = {
        'sessions': sessions,
        'count': len(sessions),
        'limit': limit
    }
    
    # Add pagination token if more results exist
    if 'LastEvaluatedKey' in response and len(sessions) >= limit:
        result['nextToken'] = json.dumps(response['LastEvaluatedKey'])
    
    logger.info(f"Found {len(sessions)} sessions")
    return result


def handle_get_analytics(user_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get aggregated analytics for user's sensors.
    
    Query Parameters:
    - sensorId: Filter by sensor ID (optional)
    - startDate: Start date (ISO format, optional, default: 30 days ago)
    - endDate: End date (ISO format, optional, default: now)
    
    Args:
        user_id: Authenticated user ID
        query_params: Query parameters
        
    Returns:
        Aggregated statistics
    """
    logger.info(f"Calculating analytics for user: {user_id}")
    
    # Parse parameters
    sensor_id = query_params.get('sensorId')
    start_date = query_params.get('startDate')
    end_date = query_params.get('endDate')
    
    # Default date range: last 30 days
    if not end_date:
        end_date = datetime.utcnow().isoformat()
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
    
    # Get user's sensors
    sensors_db = DynamoDBHelper(SENSORS_TABLE)
    user_sensors_response = sensors_db.query(
        key_condition="userId = :userId",
        index_name="UserIdIndex",
        userId=user_id
    )
    user_sensor_ids = {s['sensorId'] for s in user_sensors_response.get('Items', [])}
    
    if sensor_id and sensor_id not in user_sensor_ids:
        raise AuthorizationError(
            message="You do not have permission to access analytics for this sensor"
        )
    
    # Query sessions for analytics
    sessions_db = DynamoDBHelper(SESSIONS_TABLE)
    
    # Determine which sensors to query
    target_sensor_ids = [sensor_id] if sensor_id else list(user_sensor_ids)
    
    all_sessions = []
    for sid in target_sensor_ids:
        response = sessions_db.query(
            key_condition="sensorId = :sensorId",
            index_name="SensorIdIndex",
            sensorId=sid
        )
        all_sessions.extend(response.get('Items', []))
    
    # Filter by date range
    start_timestamp = int(datetime.fromisoformat(start_date.replace('Z', '+00:00')).timestamp())
    end_timestamp = int(datetime.fromisoformat(end_date.replace('Z', '+00:00')).timestamp())
    
    filtered_sessions = [
        s for s in all_sessions
        if start_timestamp <= s.get('startTime', 0) <= end_timestamp
    ]
    
    # Calculate analytics
    total_sessions = len(filtered_sessions)
    completed_sessions = [s for s in filtered_sessions if s.get('status') == 'completed']
    active_sessions = [s for s in filtered_sessions if s.get('status') == 'active']
    
    total_duration_minutes = sum(
        s.get('durationMinutes', 0) for s in completed_sessions
    )
    
    total_motion_events = sum(
        s.get('motionEvents', 0) for s in filtered_sessions
    )
    
    avg_duration = (
        total_duration_minutes / len(completed_sessions)
        if completed_sessions else 0
    )
    
    avg_motion_events = (
        total_motion_events / len(filtered_sessions)
        if filtered_sessions else 0
    )
    
    # Group by sensor
    by_sensor = {}
    for session in filtered_sessions:
        sid = session.get('sensorId')
        if sid not in by_sensor:
            by_sensor[sid] = {
                'sensorId': sid,
                'totalSessions': 0,
                'completedSessions': 0,
                'totalDurationMinutes': 0,
                'totalMotionEvents': 0
            }
        
        by_sensor[sid]['totalSessions'] += 1
        if session.get('status') == 'completed':
            by_sensor[sid]['completedSessions'] += 1
            by_sensor[sid]['totalDurationMinutes'] += session.get('durationMinutes', 0)
        by_sensor[sid]['totalMotionEvents'] += session.get('motionEvents', 0)
    
    # Convert Decimals
    analytics = {
        'summary': {
            'totalSessions': total_sessions,
            'completedSessions': len(completed_sessions),
            'activeSessions': len(active_sessions),
            'totalDurationMinutes': float(total_duration_minutes),
            'totalMotionEvents': total_motion_events,
            'averageDurationMinutes': round(float(avg_duration), 2),
            'averageMotionEventsPerSession': round(float(avg_motion_events), 2)
        },
        'bySensor': convert_decimals(list(by_sensor.values())),
        'dateRange': {
            'startDate': start_date,
            'endDate': end_date
        }
    }
    
    logger.info(f"Analytics calculated: {total_sessions} sessions")
    return analytics


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def validate_environment() -> None:
    """Validate required environment variables."""
    required_vars = [
        'SENSORS_TABLE',
        'USERS_TABLE',
        'SESSIONS_TABLE',
        'MOTION_EVENTS_TABLE',
        'SPOTIFY_SECRET_NAME'
    ]
    
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def parse_body(body: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse request body from JSON string."""
    if not body:
        return None
    
    if isinstance(body, dict):
        return body
    
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ValidationError(
            message=f"Invalid JSON in request body: {str(e)}",
            field="body"
        )


def extract_user_id(event: Dict[str, Any]) -> str:
    """
    Extract user ID from Cognito authorizer claims.
    
    Args:
        event: API Gateway event
        
    Returns:
        User ID from JWT token
        
    Raises:
        AuthorizationError: If user ID cannot be extracted
    """
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        user_id = claims.get('sub')
        
        if not user_id:
            raise AuthorizationError(
                message="User ID not found in authorization token"
            )
        
        return user_id
        
    except Exception as e:
        logger.error(f"Failed to extract user ID: {e}")
        raise AuthorizationError(
            message="Invalid or missing authorization token"
        )


def get_spotify_access_token(user_id: str) -> str:
    """
    Get valid Spotify access token for user.
    
    Args:
        user_id: User ID
        
    Returns:
        Valid Spotify access token
        
    Raises:
        ValidationError: If token cannot be retrieved
    """
    # Get user from DynamoDB
    dynamodb = DynamoDBHelper(USERS_TABLE)
    user = dynamodb.get_item({'userId': user_id})
    
    if not user:
        raise ResourceNotFoundError(
            message=f"User not found: {user_id}",
            resource_type="User",
            resource_id=user_id
        )
    
    # Get Spotify tokens from Secrets Manager
    secrets_helper = SecretsHelper()
    secret_name = f"{SPOTIFY_SECRET_NAME}/{user_id}"
    
    try:
        secret = secrets_helper.get_secret(secret_name)
        access_token = secret.get('access_token')
        
        if not access_token:
            raise ValidationError(
                message="Spotify access token not found. Please reconnect your Spotify account.",
                field="spotify"
            )
        
        return access_token
        
    except Exception as e:
        logger.error(f"Failed to get Spotify token: {e}")
        raise ValidationError(
            message="Failed to retrieve Spotify credentials. Please reconnect your Spotify account.",
            field="spotify"
        )


def convert_decimals(obj: Any) -> Any:
    """
    Recursively convert Decimal objects to float for JSON serialization.
    
    Args:
        obj: Object to convert
        
    Returns:
        Converted object
    """
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized API Gateway response.
    
    Args:
        status_code: HTTP status code
        body: Response body
        
    Returns:
        API Gateway response dictionary
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY'
        },
        'body': json.dumps(body)
    }
