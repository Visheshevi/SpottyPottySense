"""
Custom Exception Classes for SpottyPottySense.

This module defines a comprehensive exception hierarchy for handling
various error conditions across the application. All custom exceptions
inherit from the base SpottyPottySenseError class.

Exception Hierarchy:
    SpottyPottySenseError (Base)
    ├── SpotifyAPIError
    │   ├── SpotifyAuthenticationError
    │   ├── SpotifyRateLimitError
    │   └── SpotifyPlaybackError
    ├── DynamoDBError
    │   ├── DynamoDBThrottlingError
    │   └── DynamoDBItemNotFoundError
    ├── SecretsManagerError
    ├── ValidationError
    │   └── InvalidSensorConfigError
    ├── ConfigurationError
    ├── AuthenticationError
    ├── ResourceNotFoundError
    └── ThrottlingError

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2)
"""

from typing import Any, Dict, Optional
import json


class SpottyPottySenseError(Exception):
    """
    Base exception for all SpottyPottySense errors.
    
    All custom exceptions should inherit from this class to enable
    centralized error handling and logging.
    
    Attributes:
        message (str): Human-readable error message
        error_code (str): Machine-readable error code
        details (Dict): Additional error context
        http_status (int): Suggested HTTP status code for API responses
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        http_status: int = 500
    ):
        """
        Initialize the base exception.
        
        Args:
            message: Human-readable error description
            error_code: Machine-readable error identifier
            details: Additional context (will be sanitized in logs)
            http_status: HTTP status code for API responses
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.http_status = http_status
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary format for logging/API responses.
        
        Returns:
            Dictionary with error details
        """
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }
    
    def to_json(self) -> str:
        """
        Convert exception to JSON string.
        
        Returns:
            JSON-formatted error details
        """
        return json.dumps(self.to_dict())
    
    def __str__(self) -> str:
        """String representation of the exception."""
        if self.details:
            return f"{self.message} (Code: {self.error_code}, Details: {self.details})"
        return f"{self.message} (Code: {self.error_code})"
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"details={self.details!r}, "
            f"http_status={self.http_status})"
        )


# ==============================================================================
# SPOTIFY API EXCEPTIONS
# ==============================================================================

class SpotifyAPIError(SpottyPottySenseError):
    """
    Raised when Spotify API calls fail.
    
    This is a general exception for Spotify API errors. Use more specific
    subclasses when possible (e.g., SpotifyAuthenticationError).
    """
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Spotify API error.
        
        Args:
            message: Error description
            status_code: HTTP status code from Spotify API
            response_body: Raw response from Spotify (sanitized)
            details: Additional context
        """
        error_details = details or {}
        if status_code:
            error_details["status_code"] = status_code
        if response_body:
            # Truncate response body to avoid log bloat
            error_details["response"] = response_body[:500]
        
        super().__init__(
            message=message,
            error_code="SPOTIFY_API_ERROR",
            details=error_details,
            http_status=502  # Bad Gateway - upstream service error
        )


class SpotifyAuthenticationError(SpotifyAPIError):
    """Raised when Spotify authentication/authorization fails."""
    
    def __init__(self, message: str = "Spotify authentication failed", **kwargs):
        super().__init__(message, **kwargs)
        self.error_code = "SPOTIFY_AUTH_ERROR"
        self.http_status = 401


class SpotifyRateLimitError(SpotifyAPIError):
    """
    Raised when Spotify API rate limits are exceeded.
    
    Attributes:
        retry_after (int): Seconds to wait before retrying
    """
    
    def __init__(
        self,
        message: str = "Spotify API rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.error_code = "SPOTIFY_RATE_LIMIT"
        self.http_status = 429
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after"] = retry_after


class SpotifyPlaybackError(SpotifyAPIError):
    """Raised when Spotify playback operations fail."""
    
    def __init__(
        self,
        message: str = "Spotify playback operation failed",
        device_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.error_code = "SPOTIFY_PLAYBACK_ERROR"
        if device_id:
            self.details["device_id"] = device_id


# ==============================================================================
# DYNAMODB EXCEPTIONS
# ==============================================================================

class DynamoDBError(SpottyPottySenseError):
    """
    Raised when DynamoDB operations fail.
    
    General exception for DynamoDB errors. Use specific subclasses
    when appropriate.
    """
    
    def __init__(
        self,
        message: str,
        table_name: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if table_name:
            error_details["table_name"] = table_name
        if operation:
            error_details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code="DYNAMODB_ERROR",
            details=error_details,
            http_status=500
        )


class DynamoDBThrottlingError(DynamoDBError):
    """Raised when DynamoDB throttles requests."""
    
    def __init__(self, message: str = "DynamoDB request throttled", **kwargs):
        super().__init__(message, **kwargs)
        self.error_code = "DYNAMODB_THROTTLED"
        self.http_status = 503  # Service Unavailable


class DynamoDBItemNotFoundError(DynamoDBError):
    """Raised when a DynamoDB item is not found."""
    
    def __init__(
        self,
        message: str = "Item not found in DynamoDB",
        item_key: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.error_code = "ITEM_NOT_FOUND"
        self.http_status = 404
        if item_key:
            self.details["key"] = item_key


# ==============================================================================
# SECRETS MANAGER EXCEPTIONS
# ==============================================================================

class SecretsManagerError(SpottyPottySenseError):
    """Raised when AWS Secrets Manager operations fail."""
    
    def __init__(
        self,
        message: str,
        secret_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if secret_id:
            # Only store secret ID, never the secret value
            error_details["secret_id"] = secret_id
        
        super().__init__(
            message=message,
            error_code="SECRETS_MANAGER_ERROR",
            details=error_details,
            http_status=500
        )


# ==============================================================================
# VALIDATION EXCEPTIONS
# ==============================================================================

class ValidationError(SpottyPottySenseError):
    """
    Raised when input validation fails.
    
    Used for Pydantic validation errors and custom validation logic.
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            # Convert to string to avoid logging sensitive data
            error_details["invalid_value"] = str(value)[:100]
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details,
            http_status=400  # Bad Request
        )


class InvalidSensorConfigError(ValidationError):
    """Raised when sensor configuration is invalid."""
    
    def __init__(self, message: str = "Invalid sensor configuration", **kwargs):
        super().__init__(message, **kwargs)
        self.error_code = "INVALID_SENSOR_CONFIG"


# ==============================================================================
# CONFIGURATION EXCEPTIONS
# ==============================================================================

class ConfigurationError(SpottyPottySenseError):
    """Raised when application configuration is invalid or missing."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=error_details,
            http_status=500
        )


# ==============================================================================
# AUTHENTICATION & AUTHORIZATION EXCEPTIONS
# ==============================================================================

class AuthenticationError(SpottyPottySenseError):
    """Raised when user authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            http_status=401  # Unauthorized
        )


class AuthorizationError(SpottyPottySenseError):
    """Raised when user is not authorized to perform an action."""
    
    def __init__(
        self,
        message: str = "Not authorized to perform this action",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if required_permission:
            error_details["required_permission"] = required_permission
        
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=error_details,
            http_status=403  # Forbidden
        )


# ==============================================================================
# RESOURCE EXCEPTIONS
# ==============================================================================

class ResourceNotFoundError(SpottyPottySenseError):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=error_details,
            http_status=404  # Not Found
        )


class ResourceConflictError(SpottyPottySenseError):
    """Raised when a resource already exists or conflicts with existing data."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code="RESOURCE_CONFLICT",
            details=error_details,
            http_status=409  # Conflict
        )


# ==============================================================================
# THROTTLING & RATE LIMIT EXCEPTIONS
# ==============================================================================

class ThrottlingError(SpottyPottySenseError):
    """
    Raised when rate limits are exceeded (general).
    
    For service-specific throttling, use appropriate subclasses
    (e.g., SpotifyRateLimitError, DynamoDBThrottlingError).
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            error_code="THROTTLING_ERROR",
            details=error_details,
            http_status=429  # Too Many Requests
        )
        self.retry_after = retry_after


# ==============================================================================
# TIMEOUT EXCEPTIONS
# ==============================================================================

class TimeoutError(SpottyPottySenseError):
    """Raised when an operation times out."""
    
    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if timeout_seconds:
            error_details["timeout_seconds"] = timeout_seconds
        
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            details=error_details,
            http_status=504  # Gateway Timeout
        )

