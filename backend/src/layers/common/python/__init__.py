"""
Common Layer - Shared utilities for Lambda functions.

This is a STUB implementation for Phase 1 deployment.
Full implementation will be added in Phase 2.
"""

__version__ = '1.0.0'

from .spotify_client import SpotifyClient
from .dynamodb_helper import DynamoDBHelper
from .secrets_helper import SecretsHelper
from .validation import (
    validate_sensor,
    validate_user,
    validate_session,
    validate_motion_event
)
from .exceptions import (
    SpottyPottySenseError,
    SpotifyAPIError,
    DynamoDBError,
    ValidationError,
    ConfigurationError,
    AuthenticationError,
    ResourceNotFoundError,
    ThrottlingError
)
from .logger import setup_logger, log_with_context, sanitize_log_data

__all__ = [
    'SpotifyClient',
    'DynamoDBHelper',
    'SecretsHelper',
    'validate_sensor',
    'validate_user',
    'validate_session',
    'validate_motion_event',
    'SpottyPottySenseError',
    'SpotifyAPIError',
    'DynamoDBError',
    'ValidationError',
    'ConfigurationError',
    'AuthenticationError',
    'ResourceNotFoundError',
    'ThrottlingError',
    'setup_logger',
    'log_with_context',
    'sanitize_log_data',
]

