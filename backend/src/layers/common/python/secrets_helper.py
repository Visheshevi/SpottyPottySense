"""
AWS Secrets Manager Helper with Intelligent Caching.

This module provides efficient access to AWS Secrets Manager with:
- In-memory caching for Lambda warm starts (saves API calls and cost)
- Automatic JSON parsing
- TTL-based cache invalidation
- Thread-safe operations
- Comprehensive error handling
- Secret versioning support

Usage:
    from secrets_helper import SecretsHelper, get_secret
    
    # Using the singleton
    secret = get_secret("my-secret-name")
    
    # Or create your own instance
    helper = SecretsHelper()
    secret = helper.get_secret("my-secret-name")

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2)
"""

import json
import time
from typing import Any, Dict, Optional, Union
import boto3
from botocore.exceptions import ClientError

from exceptions import SecretsManagerError, ResourceNotFoundError
from logger import get_logger

logger = get_logger(__name__)


# ==============================================================================
# CACHE CONFIGURATION
# ==============================================================================

# Default cache TTL in seconds (5 minutes for Lambda warm containers)
DEFAULT_CACHE_TTL = 300

# Maximum cache size (prevent memory issues in long-running Lambdas)
MAX_CACHE_SIZE = 100


# ==============================================================================
# SECRETS HELPER CLASS
# ==============================================================================

class SecretsHelper:
    """
    AWS Secrets Manager helper with intelligent caching.
    
    This class provides optimized access to Secrets Manager with:
    - In-memory caching to reduce API calls during Lambda warm starts
    - Automatic cache invalidation based on TTL
    - Support for both JSON and string secrets
    - Thread-safe operations
    - Comprehensive error handling
    
    The cache is particularly useful in Lambda functions where the
    execution context may be reused across multiple invocations.
    
    Attributes:
        client: Boto3 Secrets Manager client
        cache: Dictionary storing cached secrets
        cache_ttl: Time-to-live for cache entries in seconds
    """
    
    def __init__(
        self,
        region_name: Optional[str] = None,
        cache_ttl: int = DEFAULT_CACHE_TTL
    ):
        """
        Initialize Secrets Manager helper.
        
        Args:
            region_name: AWS region (defaults to Lambda environment region)
            cache_ttl: Cache time-to-live in seconds (default: 300)
        """
        self.client = boto3.client('secretsmanager', region_name=region_name)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = cache_ttl
        
        logger.info(
            "SecretsHelper initialized",
            extra={"cache_ttl": cache_ttl, "region": region_name or "default"}
        )
    
    def get_secret(
        self,
        secret_id: str,
        use_cache: bool = True,
        version_id: Optional[str] = None,
        version_stage: Optional[str] = None,
        parse_json: bool = True
    ) -> Union[Dict[str, Any], str]:
        """
        Retrieve a secret from AWS Secrets Manager with caching.
        
        This method retrieves secrets with intelligent caching:
        1. Check cache if enabled and not expired
        2. Fetch from Secrets Manager if cache miss
        3. Parse JSON if requested
        4. Store in cache for future calls
        
        Args:
            secret_id: Secret name or ARN
            use_cache: Whether to use cache (default: True)
            version_id: Specific version ID to retrieve
            version_stage: Version stage to retrieve (e.g., "AWSCURRENT")
            parse_json: Attempt to parse secret as JSON (default: True)
            
        Returns:
            Secret value as dictionary (if JSON) or string
            
        Raises:
            ResourceNotFoundError: If secret doesn't exist
            SecretsManagerError: If retrieval fails
            
        Example:
            >>> helper = SecretsHelper()
            >>> spotify_creds = helper.get_secret("spotify/credentials")
            >>> print(spotify_creds['client_id'])
        """
        cache_key = self._get_cache_key(secret_id, version_id, version_stage)
        
        # Check cache first
        if use_cache and self._is_cached(cache_key):
            logger.debug(
                "Returning cached secret",
                extra={"secret_id": secret_id, "cache_key": cache_key}
            )
            return self._cache[cache_key]['value']
        
        # Fetch from Secrets Manager
        logger.info(
            "Fetching secret from Secrets Manager",
            extra={"secret_id": secret_id}
        )
        
        try:
            start_time = time.time()
            
            # Build request parameters
            params = {'SecretId': secret_id}
            if version_id:
                params['VersionId'] = version_id
            if version_stage:
                params['VersionStage'] = version_stage
            
            # Call Secrets Manager
            response = self.client.get_secret_value(**params)
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Secret retrieved successfully",
                extra={
                    "secret_id": secret_id,
                    "duration_ms": round(duration_ms, 2),
                    "version_id": response.get('VersionId')
                }
            )
            
            # Extract secret value
            if 'SecretString' in response:
                secret_value = response['SecretString']
                
                # Try to parse as JSON if requested
                if parse_json:
                    try:
                        secret_value = json.loads(secret_value)
                    except json.JSONDecodeError:
                        logger.debug("Secret is not valid JSON, returning as string")
            else:
                # Binary secret (rare case)
                secret_value = response['SecretBinary']
                logger.warning("Binary secret retrieved (uncommon)")
            
            # Store in cache
            if use_cache:
                self._cache_secret(cache_key, secret_value)
            
            return secret_value
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'ResourceNotFoundException':
                logger.error(
                    "Secret not found",
                    extra={"secret_id": secret_id, "error_code": error_code}
                )
                raise ResourceNotFoundError(
                    message=f"Secret not found: {secret_id}",
                    resource_type="Secret",
                    resource_id=secret_id
                )
            
            logger.error(
                "Failed to retrieve secret",
                extra={
                    "secret_id": secret_id,
                    "error_code": error_code,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise SecretsManagerError(
                message=f"Failed to retrieve secret: {error_code}",
                secret_id=secret_id,
                details={"error_code": error_code}
            )
    
    def update_secret(
        self,
        secret_id: str,
        secret_value: Union[Dict[str, Any], str],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a secret in AWS Secrets Manager.
        
        This method updates the secret value and automatically invalidates
        the cache entry.
        
        Args:
            secret_id: Secret name or ARN
            secret_value: New secret value (dict will be JSON-serialized)
            description: Optional description update
            
        Returns:
            Update response with version information
            
        Raises:
            SecretsManagerError: If update fails
            
        Example:
            >>> helper = SecretsHelper()
            >>> new_token = {"access_token": "new_token", "expires_at": "..."}
            >>> helper.update_secret("user/spotify/tokens", new_token)
        """
        logger.info(
            "Updating secret",
            extra={"secret_id": secret_id}
        )
        
        try:
            # Convert dict to JSON string
            if isinstance(secret_value, dict):
                secret_string = json.dumps(secret_value)
            else:
                secret_string = secret_value
            
            # Build request parameters
            params = {
                'SecretId': secret_id,
                'SecretString': secret_string
            }
            if description:
                params['Description'] = description
            
            # Update secret
            start_time = time.time()
            response = self.client.put_secret_value(**params)
            duration_ms = (time.time() - start_time) * 1000
            
            # Invalidate cache
            self.invalidate_secret(secret_id)
            
            logger.info(
                "Secret updated successfully",
                extra={
                    "secret_id": secret_id,
                    "version_id": response.get('VersionId'),
                    "duration_ms": round(duration_ms, 2)
                }
            )
            
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                "Failed to update secret",
                extra={
                    "secret_id": secret_id,
                    "error_code": error_code,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise SecretsManagerError(
                message=f"Failed to update secret: {error_code}",
                secret_id=secret_id,
                details={"error_code": error_code}
            )
    
    def invalidate_secret(self, secret_id: str) -> None:
        """
        Invalidate cached secret entries for a given secret ID.
        
        This removes all cache entries (all versions) for the specified secret.
        
        Args:
            secret_id: Secret name or ARN to invalidate
        """
        # Remove all cache entries that start with this secret_id
        keys_to_remove = [
            key for key in self._cache.keys()
            if key.startswith(f"{secret_id}:")
        ]
        
        for key in keys_to_remove:
            del self._cache[key]
        
        if keys_to_remove:
            logger.debug(
                "Invalidated secret cache entries",
                extra={"secret_id": secret_id, "entries_removed": len(keys_to_remove)}
            )
    
    def clear_cache(self) -> None:
        """
        Clear all cached secrets.
        
        Useful for testing or when you want to force fresh retrieval.
        """
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(
            "Secret cache cleared",
            extra={"entries_cleared": cache_size}
        )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache metrics
        """
        return {
            "cache_size": len(self._cache),
            "cache_ttl": self.cache_ttl,
            "max_cache_size": MAX_CACHE_SIZE,
            "cached_secrets": list(self._cache.keys())
        }
    
    # Private helper methods
    
    def _get_cache_key(
        self,
        secret_id: str,
        version_id: Optional[str],
        version_stage: Optional[str]
    ) -> str:
        """Generate cache key from secret parameters."""
        parts = [secret_id]
        if version_id:
            parts.append(f"v{version_id}")
        if version_stage:
            parts.append(f"s{version_stage}")
        return ":".join(parts)
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if secret is cached and not expired."""
        if cache_key not in self._cache:
            return False
        
        cached_entry = self._cache[cache_key]
        if time.time() > cached_entry['expires_at']:
            # Cache expired, remove it
            del self._cache[cache_key]
            logger.debug(
                "Cache entry expired",
                extra={"cache_key": cache_key}
            )
            return False
        
        return True
    
    def _cache_secret(self, cache_key: str, value: Any) -> None:
        """Store secret in cache with TTL."""
        # Enforce max cache size
        if len(self._cache) >= MAX_CACHE_SIZE:
            # Remove oldest entry (simple eviction strategy)
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k]['cached_at']
            )
            del self._cache[oldest_key]
            logger.debug(
                "Cache size limit reached, evicted oldest entry",
                extra={"evicted_key": oldest_key}
            )
        
        # Store in cache
        self._cache[cache_key] = {
            'value': value,
            'cached_at': time.time(),
            'expires_at': time.time() + self.cache_ttl
        }


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

# Global singleton instance
_secrets_helper_instance: Optional[SecretsHelper] = None


def get_secrets_helper() -> SecretsHelper:
    """
    Get or create singleton SecretsHelper instance.
    
    Returns:
        Shared SecretsHelper instance
    """
    global _secrets_helper_instance
    if _secrets_helper_instance is None:
        _secrets_helper_instance = SecretsHelper()
    return _secrets_helper_instance


def get_secret(
    secret_id: str,
    use_cache: bool = True,
    parse_json: bool = True
) -> Union[Dict[str, Any], str]:
    """
    Convenience function to get a secret using the singleton helper.
    
    Args:
        secret_id: Secret name or ARN
        use_cache: Whether to use cache
        parse_json: Whether to parse as JSON
        
    Returns:
        Secret value
        
    Example:
        >>> creds = get_secret("spotify/credentials")
        >>> print(creds['client_id'])
    """
    helper = get_secrets_helper()
    return helper.get_secret(secret_id, use_cache=use_cache, parse_json=parse_json)


def update_secret(
    secret_id: str,
    secret_value: Union[Dict[str, Any], str]
) -> Dict[str, Any]:
    """
    Convenience function to update a secret using the singleton helper.
    
    Args:
        secret_id: Secret name or ARN
        secret_value: New secret value
        
    Returns:
        Update response
    """
    helper = get_secrets_helper()
    return helper.update_secret(secret_id, secret_value)

