"""
SpottyPottySense Common Lambda Layer.

This package provides shared utilities, clients, and helpers for all Lambda functions:
- Spotify API client with OAuth and playback control
- DynamoDB helper with CRUD operations and retry logic
- Secrets Manager helper with intelligent caching
- Pydantic data models for validation
- Custom exception classes
- Structured logging with AWS Lambda Powertools

Version: 2.0.0 (Phase 2)
Author: SpottyPottySense Team
"""

__version__ = '2.0.0'
__author__ = 'SpottyPottySense Team'

# Import main classes
from .spotify_client import SpotifyClient
from .dynamodb_helper import DynamoDBHelper, python_to_dynamodb, dynamodb_to_python
from .secrets_helper import SecretsHelper, get_secret, update_secret, get_secrets_helper

# Import validation models and functions
from .validation import (
    # Models
    Sensor,
    User,
    Session,
    MotionEvent,
    QuietHours,
    SpotifyPlaybackConfig,
    UserPreferences,
    SpotifyTokens,
    # Enums
    SensorStatus,
    SessionStatus,
    MotionEventType,
    SpotifyPlaybackState,
    # API Models
    CreateSensorRequest,
    UpdateSensorRequest,
    UpdateUserRequest,
    ApiResponse,
    PaginatedResponse,
    # Validation functions
    validate_sensor_data,
    validate_user_data,
    validate_session_data,
    validate_motion_event_data
)

# Import all exception classes
from .exceptions import (
    # Base
    SpottyPottySenseError,
    # Spotify
    SpotifyAPIError,
    SpotifyAuthenticationError,
    SpotifyRateLimitError,
    SpotifyPlaybackError,
    # DynamoDB
    DynamoDBError,
    DynamoDBThrottlingError,
    DynamoDBItemNotFoundError,
    # Secrets Manager
    SecretsManagerError,
    # Validation
    ValidationError,
    InvalidSensorConfigError,
    # Configuration
    ConfigurationError,
    # Authentication & Authorization
    AuthenticationError,
    AuthorizationError,
    # Resources
    ResourceNotFoundError,
    ResourceConflictError,
    # Rate Limiting
    ThrottlingError,
    # Timeout
    TimeoutError
)

# Import logging utilities
from .logger import (
    get_logger,
    get_secrets_helper,
    inject_lambda_context,
    add_persistent_context,
    remove_persistent_context,
    clear_context,
    sanitize_log_data,
    mask_email,
    log_error,
    log_performance,
    log_api_call,
    with_logger
)

# Define public API
__all__ = [
    # Version
    '__version__',
    '__author__',
    
    # Main Classes
    'SpotifyClient',
    'DynamoDBHelper',
    'SecretsHelper',
    
    # DynamoDB Helpers
    'python_to_dynamodb',
    'dynamodb_to_python',
    
    # Secrets Helpers
    'get_secret',
    'update_secret',
    'get_secrets_helper',
    
    # Validation Models
    'Sensor',
    'User',
    'Session',
    'MotionEvent',
    'QuietHours',
    'SpotifyPlaybackConfig',
    'UserPreferences',
    'SpotifyTokens',
    
    # Enums
    'SensorStatus',
    'SessionStatus',
    'MotionEventType',
    'SpotifyPlaybackState',
    
    # API Models
    'CreateSensorRequest',
    'UpdateSensorRequest',
    'UpdateUserRequest',
    'ApiResponse',
    'PaginatedResponse',
    
    # Validation Functions
    'validate_sensor_data',
    'validate_user_data',
    'validate_session_data',
    'validate_motion_event_data',
    
    # Exceptions
    'SpottyPottySenseError',
    'SpotifyAPIError',
    'SpotifyAuthenticationError',
    'SpotifyRateLimitError',
    'SpotifyPlaybackError',
    'DynamoDBError',
    'DynamoDBThrottlingError',
    'DynamoDBItemNotFoundError',
    'SecretsManagerError',
    'ValidationError',
    'InvalidSensorConfigError',
    'ConfigurationError',
    'AuthenticationError',
    'AuthorizationError',
    'ResourceNotFoundError',
    'ResourceConflictError',
    'ThrottlingError',
    'TimeoutError',
    
    # Logger
    'get_logger',
    'inject_lambda_context',
    'add_persistent_context',
    'remove_persistent_context',
    'clear_context',
    'sanitize_log_data',
    'mask_email',
    'log_error',
    'log_performance',
    'log_api_call',
    'with_logger',
]

