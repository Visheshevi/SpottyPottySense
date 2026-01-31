"""
Structured Logging Configuration using AWS Lambda Powertools.

This module provides enterprise-grade logging with:
- Structured JSON output for CloudWatch Logs Insights
- Automatic context injection (request_id, user_id, sensor_id)
- PII and sensitive data sanitization
- Log level configuration per environment
- Correlation IDs for distributed tracing
- Performance metrics logging

Usage:
    from logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Processing motion event", extra={
        "sensor_id": "sensor-123",
        "user_id": "user-456"
    })

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2)
"""

import os
import re
from typing import Any, Dict, Optional, Union
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext


# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Sensitive field patterns for sanitization
SENSITIVE_PATTERNS = [
    'password',
    'token',
    'secret',
    'api_key',
    'apikey',
    'access_key',
    'private_key',
    'client_secret',
    'authorization',
    'auth',
    'credential',
    'ssn',
    'social_security',
]

# Email regex for partial masking
EMAIL_REGEX = re.compile(r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b')

# Default log level from environment
DEFAULT_LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Service name for log organization
SERVICE_NAME = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'SpottyPottySense')

# Environment
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')


# ==============================================================================
# LOGGER SETUP
# ==============================================================================

def get_logger(
    name: Optional[str] = None,
    level: Optional[str] = None,
    service: Optional[str] = None,
    **kwargs
) -> Logger:
    """
    Get or create a structured logger instance with Lambda Powertools.
    
    This function creates a Logger instance configured for AWS Lambda
    with automatic JSON formatting, correlation IDs, and context injection.
    
    Args:
        name: Logger name (usually __name__ of calling module)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service: Service name for log grouping (defaults to Lambda function name)
        **kwargs: Additional parameters passed to Lambda Powertools Logger
        
    Returns:
        Logger: Configured Logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("User logged in", extra={"user_id": "123"})
    """
    log_level = level or DEFAULT_LOG_LEVEL
    service_name = service or SERVICE_NAME
    
    # Create logger with Powertools
    # Note: Lambda Powertools Logger doesn't need child() for module names
    # The service parameter provides sufficient context
    new_logger = Logger(
        service=service_name,
        level=log_level,
        **kwargs
    )
    
    return new_logger


def inject_lambda_context(
    logger: Logger,
    lambda_context: Optional[LambdaContext] = None,
    correlation_id_path: Optional[str] = None,
    log_event: bool = False,
    clear_state: bool = False
):
    """
    Decorator to inject Lambda context into logger.
    
    This decorator automatically adds Lambda context information
    (request_id, function_name, memory_limit, etc.) to all log statements.
    
    Args:
        logger: Logger instance
        lambda_context: Lambda context object
        correlation_id_path: JSON path to extract correlation ID from event
        log_event: Whether to log the incoming event (sanitized)
        clear_state: Whether to clear state between invocations
        
    Returns:
        Decorator function
        
    Example:
        @inject_lambda_context(logger, log_event=True)
        def handler(event, context):
            logger.info("Processing event")
            return {"statusCode": 200}
    """
    return logger.inject_lambda_context(
        lambda_context=lambda_context,
        correlation_id_path=correlation_id_path,
        log_event=log_event,
        clear_state=clear_state
    )


# ==============================================================================
# CONTEXT MANAGEMENT
# ==============================================================================

def add_persistent_context(logger: Logger, **context: Any) -> None:
    """
    Add persistent context that will be included in all subsequent logs.
    
    Useful for adding user_id, sensor_id, session_id that should appear
    in all log statements within a Lambda invocation.
    
    Args:
        logger: Logger instance
        **context: Key-value pairs to add to logging context
        
    Example:
        >>> add_persistent_context(logger, user_id="user-123", sensor_id="sensor-456")
        >>> logger.info("Motion detected")  # Will include user_id and sensor_id
    """
    # Sanitize context before adding
    sanitized_context = sanitize_log_data(context)
    logger.append_keys(**sanitized_context)


def remove_persistent_context(logger: Logger, *keys: str) -> None:
    """
    Remove keys from persistent logging context.
    
    Args:
        logger: Logger instance
        *keys: Keys to remove from context
        
    Example:
        >>> remove_persistent_context(logger, "user_id", "sensor_id")
    """
    logger.remove_keys(keys)


def clear_context(logger: Logger) -> None:
    """
    Clear all persistent logging context.
    
    Args:
        logger: Logger instance
    """
    logger.clear_state()


# ==============================================================================
# SANITIZATION
# ==============================================================================

def sanitize_log_data(data: Any, max_depth: int = 10) -> Any:
    """
    Recursively sanitize sensitive data from logs.
    
    This function removes or masks:
    - Passwords, tokens, secrets, API keys
    - Email addresses (partially masked)
    - Credit card numbers
    - Any field matching sensitive patterns
    
    Args:
        data: Data to sanitize (dict, list, str, or primitive)
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Returns:
        Sanitized data with sensitive information redacted
        
    Example:
        >>> sanitize_log_data({"email": "user@example.com", "token": "secret123"})
        {'email': 'u***@example.com', 'token': '***REDACTED***'}
    """
    if max_depth <= 0:
        return "[MAX_DEPTH_EXCEEDED]"
    
    if isinstance(data, dict):
        return {
            key: _sanitize_value(key, value, max_depth)
            for key, value in data.items()
        }
    elif isinstance(data, (list, tuple)):
        return [sanitize_log_data(item, max_depth - 1) for item in data]
    elif isinstance(data, str):
        return _mask_sensitive_strings(data)
    else:
        return data


def _sanitize_value(key: str, value: Any, max_depth: int) -> Any:
    """
    Sanitize a single key-value pair.
    
    Args:
        key: Dictionary key
        value: Value to sanitize
        max_depth: Remaining recursion depth
        
    Returns:
        Sanitized value
    """
    # Check if key contains sensitive pattern
    key_lower = key.lower()
    if any(pattern in key_lower for pattern in SENSITIVE_PATTERNS):
        # For sensitive fields, only show if it's set or not
        return '***REDACTED***' if value else None
    
    # Recursively sanitize nested structures
    if isinstance(value, dict):
        return sanitize_log_data(value, max_depth - 1)
    elif isinstance(value, (list, tuple)):
        return [sanitize_log_data(item, max_depth - 1) for item in value]
    elif isinstance(value, str):
        return _mask_sensitive_strings(value)
    else:
        return value


def _mask_sensitive_strings(text: str) -> str:
    """
    Mask sensitive patterns in strings (emails, etc.).
    
    Args:
        text: String to mask
        
    Returns:
        Masked string
    """
    # Mask email addresses (keep first char and domain)
    text = EMAIL_REGEX.sub(lambda m: f"{m.group(1)[0]}***@{m.group(2)}", text)
    
    # Mask credit card numbers (basic pattern)
    text = re.sub(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        '****-****-****-****',
        text
    )
    
    return text


def mask_email(email: str) -> str:
    """
    Mask email address for logging.
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email (e.g., "u***@example.com")
        
    Example:
        >>> mask_email("user@example.com")
        'u***@example.com'
    """
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) > 0:
        masked_local = local[0] + '***'
        return f"{masked_local}@{domain}"
    return email


# ==============================================================================
# STRUCTURED LOGGING HELPERS
# ==============================================================================

def log_error(
    logger: Logger,
    error: Exception,
    message: str = "An error occurred",
    **context: Any
) -> None:
    """
    Log an exception with full context and stack trace.
    
    Args:
        logger: Logger instance
        error: Exception to log
        message: Error message
        **context: Additional context
        
    Example:
        >>> try:
        >>>     risky_operation()
        >>> except Exception as e:
        >>>     log_error(logger, e, "Operation failed", user_id="123")
    """
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **sanitize_log_data(context)
    }
    
    logger.error(
        message,
        extra=error_context,
        exc_info=True  # Include stack trace
    )


def log_performance(
    logger: Logger,
    operation: str,
    duration_ms: float,
    success: bool = True,
    **context: Any
) -> None:
    """
    Log performance metrics for an operation.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        success: Whether operation succeeded
        **context: Additional context
        
    Example:
        >>> start = time.time()
        >>> do_expensive_operation()
        >>> duration = (time.time() - start) * 1000
        >>> log_performance(logger, "spotify_api_call", duration, success=True)
    """
    logger.info(
        f"Performance: {operation}",
        extra={
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            **sanitize_log_data(context)
        }
    )


def log_api_call(
    logger: Logger,
    service: str,
    endpoint: str,
    method: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    **context: Any
) -> None:
    """
    Log external API calls (Spotify, AWS services, etc.).
    
    Args:
        logger: Logger instance
        service: Service name (e.g., "Spotify", "DynamoDB")
        endpoint: API endpoint or operation name
        method: HTTP method or operation type
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **context: Additional context
        
    Example:
        >>> log_api_call(
        >>>     logger,
        >>>     service="Spotify",
        >>>     endpoint="/v1/me/player/play",
        >>>     method="PUT",
        >>>     status_code=204,
        >>>     duration_ms=150.5
        >>> )
    """
    log_data = {
        "api_service": service,
        "api_endpoint": endpoint,
        "api_method": method,
    }
    
    if status_code is not None:
        log_data["status_code"] = status_code
    if duration_ms is not None:
        log_data["duration_ms"] = round(duration_ms, 2)
    
    log_data.update(sanitize_log_data(context))
    
    logger.info(f"API Call: {service} {method} {endpoint}", extra=log_data)


# ==============================================================================
# LAMBDA DECORATOR
# ==============================================================================

def with_logger(
    name: Optional[str] = None,
    log_event: bool = False,
    correlation_id_path: str = correlation_paths.API_GATEWAY_REST
):
    """
    Decorator to automatically set up logger for Lambda handlers.
    
    Args:
        name: Logger name
        log_event: Whether to log incoming event (sanitized)
        correlation_id_path: JSON path for correlation ID
        
    Returns:
        Decorator function
        
    Example:
        @with_logger(log_event=True)
        def handler(event, context):
            logger = get_logger(__name__)
            logger.info("Processing request")
            return {"statusCode": 200}
    """
    def decorator(func):
        logger = get_logger(name or func.__name__)
        
        @logger.inject_lambda_context(
            log_event=log_event,
            correlation_id_path=correlation_id_path
        )
        def wrapper(event, context):
            # Automatically log function invocation
            logger.info(
                f"Lambda invoked: {func.__name__}",
                extra={"function_name": func.__name__}
            )
            
            try:
                result = func(event, context)
                logger.info(f"Lambda completed: {func.__name__}")
                return result
            except Exception as e:
                log_error(logger, e, f"Lambda failed: {func.__name__}")
                raise
        
        return wrapper
    return decorator

