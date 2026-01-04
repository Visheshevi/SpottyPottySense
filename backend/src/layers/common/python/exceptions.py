"""
Exceptions - Custom exception classes.

This is a STUB implementation for Phase 1 deployment.
Full implementation will be added in Phase 2.
"""


class SpottyPottySenseError(Exception):
    """Base exception for SpottyPottySense errors."""
    pass


class SpotifyAPIError(SpottyPottySenseError):
    """Raised when Spotify API calls fail."""
    pass


class DynamoDBError(SpottyPottySenseError):
    """Raised when DynamoDB operations fail."""
    pass


class ValidationError(SpottyPottySenseError):
    """Raised when input validation fails."""
    pass


class ConfigurationError(SpottyPottySenseError):
    """Raised when configuration is invalid or missing."""
    pass


class AuthenticationError(SpottyPottySenseError):
    """Raised when authentication fails."""
    pass


class ResourceNotFoundError(SpottyPottySenseError):
    """Raised when a resource is not found."""
    pass


class ThrottlingError(SpottyPottySenseError):
    """Raised when rate limits are exceeded."""
    pass

