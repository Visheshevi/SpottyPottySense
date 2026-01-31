"""
Token Refresher Lambda Function

Periodically refreshes Spotify OAuth access tokens for all active users.
This function is triggered by EventBridge on a schedule (every 30 minutes)
to ensure tokens remain valid before they expire (typically 1 hour).

Flow:
1. Query all active users with Spotify connected from DynamoDB
2. For each user:
   - Retrieve refresh_token from Secrets Manager
   - Call Spotify API to refresh access_token
   - Update new access_token in Secrets Manager
3. Track and log success/failure statistics
4. Handle per-user errors gracefully (one failure doesn't stop others)

Environment Variables:
- USERS_TABLE: DynamoDB Users table name
- SPOTIFY_CREDENTIALS_SECRET: Spotify client credentials secret name
- LOG_LEVEL: Logging level (default: INFO)

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2)
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

# Import from common layer
from logger import get_logger, log_error, log_performance
from dynamodb_helper import DynamoDBHelper
from secrets_helper import get_secret, SecretsHelper
from spotify_client import SpotifyClient
from exceptions import (
    SpotifyAuthenticationError,
    SecretsManagerError,
    DynamoDBError
)

# Initialize logger
logger = get_logger(__name__)

# Environment variables
USERS_TABLE = os.environ.get('USERS_TABLE')
SPOTIFY_CREDENTIALS_SECRET = os.environ.get('SPOTIFY_CREDENTIALS_SECRET')

# Constants
TOKEN_REFRESH_BUFFER_MINUTES = 5  # Refresh tokens 5 minutes before expiry


def handler(event, context):
    """
    Lambda handler for scheduled Spotify token refresh.
    
    This function is triggered by EventBridge on a schedule to refresh
    Spotify access tokens for all active users before they expire.
    
    Args:
        event: EventBridge scheduled event
        context: Lambda context object
        
    Returns:
        dict: Summary of refresh operations with statistics
        
    Example Response:
        {
            "statusCode": 200,
            "timestamp": "2026-01-17T20:00:00Z",
            "statistics": {
                "users_queried": 10,
                "tokens_refreshed": 8,
                "tokens_skipped": 1,
                "failures": 1
            },
            "duration_ms": 2500,
            "errors": [...]
        }
    """
    start_time = time.time()
    
    logger.info(
        "Token Refresher Lambda invoked",
        extra={
            "function_name": context.function_name,
            "request_id": context.aws_request_id,
            "event_source": event.get("source", "unknown")
        }
    )
    
    # Statistics tracking
    stats = {
        "users_queried": 0,
        "tokens_refreshed": 0,
        "tokens_skipped": 0,
        "failures": 0,
        "errors": []
    }
    
    try:
        # Validate environment variables
        if not USERS_TABLE:
            raise ValueError("USERS_TABLE environment variable not set")
        if not SPOTIFY_CREDENTIALS_SECRET:
            raise ValueError("SPOTIFY_CREDENTIALS_SECRET environment variable not set")
        
        # Get Spotify client credentials
        logger.info("Retrieving Spotify client credentials")
        spotify_creds = get_secret(SPOTIFY_CREDENTIALS_SECRET)
        client_id = spotify_creds.get('client_id')
        client_secret = spotify_creds.get('client_secret')
        
        if not client_id or not client_secret:
            raise ValueError("Invalid Spotify credentials in secret")
        
        # Query all active users with Spotify connected
        logger.info("Querying active users from DynamoDB")
        users = query_active_users()
        stats["users_queried"] = len(users)
        
        logger.info(
            f"Found {len(users)} active users with Spotify connected",
            extra={"user_count": len(users)}
        )
        
        # Refresh tokens for each user
        for user in users:
            user_id = user.get('userId')
            logger.info(f"Processing user: {user_id}")
            
            try:
                # Refresh token for this user
                refreshed = refresh_user_token(
                    user=user,
                    client_id=client_id,
                    client_secret=client_secret
                )
                
                if refreshed:
                    stats["tokens_refreshed"] += 1
                    logger.info(
                        f"Token refreshed successfully for user {user_id}",
                        extra={"user_id": user_id}
                    )
                else:
                    stats["tokens_skipped"] += 1
                    logger.info(
                        f"Token refresh skipped for user {user_id} (not needed yet)",
                        extra={"user_id": user_id}
                    )
                    
            except Exception as e:
                # Log error but continue processing other users
                stats["failures"] += 1
                error_detail = {
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
                stats["errors"].append(error_detail)
                
                log_error(
                    logger,
                    e,
                    f"Failed to refresh token for user {user_id}",
                    user_id=user_id
                )
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log summary
        logger.info(
            "Token refresh completed",
            extra={
                "statistics": stats,
                "duration_ms": round(duration_ms, 2)
            }
        )
        
        # Log performance
        log_performance(
            logger,
            "token_refresh_batch",
            duration_ms,
            success=stats["failures"] == 0,
            users_processed=stats["users_queried"],
            tokens_refreshed=stats["tokens_refreshed"]
        )
        
        # Build response
        response = {
            "statusCode": 200,
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": stats,
            "duration_ms": round(duration_ms, 2)
        }
        
        return response
        
    except Exception as e:
        # Log critical error
        log_error(logger, e, "Critical error in token refresh process")
        
        duration_ms = (time.time() - start_time) * 1000
        
        return {
            "statusCode": 500,
            "timestamp": datetime.utcnow().isoformat(),
            "error": type(e).__name__,
            "message": str(e),
            "statistics": stats,
            "duration_ms": round(duration_ms, 2)
        }


def query_active_users() -> List[Dict[str, Any]]:
    """
    Query all active users who have Spotify connected from DynamoDB.
    
    This function scans the Users table (since we need all users,
    not filtering by partition key) and returns only active users
    with Spotify integration enabled.
    
    Returns:
        List of user dictionaries
        
    Raises:
        DynamoDBError: If query fails
    """
    try:
        dynamodb = DynamoDBHelper(USERS_TABLE)
        
        # In a production system with many users, we'd use pagination
        # For now, we'll do a simple scan with filter
        # Note: Scan is acceptable here because this runs infrequently (every 30 min)
        # and user count is relatively low
        
        # For Phase 2, we'll use scan
        # TODO Phase 3: Add GSI for spotify_connected status for more efficient queries
        
        from boto3.dynamodb.conditions import Attr
        
        response = dynamodb.table.scan(
            FilterExpression=Attr('active').eq(True) & Attr('spotify_connected').eq(True)
        )
        
        users = response.get('Items', [])
        
        # Handle pagination if there are many users
        while 'LastEvaluatedKey' in response:
            response = dynamodb.table.scan(
                FilterExpression=Attr('active').eq(True) & Attr('spotify_connected').eq(True),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            users.extend(response.get('Items', []))
        
        logger.info(
            f"Scanned Users table, found {len(users)} active Spotify users",
            extra={"active_spotify_users": len(users)}
        )
        
        return users
        
    except Exception as e:
        logger.error(f"Failed to query active users: {str(e)}", exc_info=True)
        raise DynamoDBError(
            message="Failed to query active users from DynamoDB",
            table_name=USERS_TABLE,
            operation="scan"
        )


def refresh_user_token(
    user: Dict[str, Any],
    client_id: str,
    client_secret: str
) -> bool:
    """
    Refresh Spotify access token for a single user.
    
    This function:
    1. Gets user's Spotify tokens from Secrets Manager
    2. Checks if token needs refresh (based on expiry time)
    3. If needed, calls Spotify API to refresh
    4. Updates Secrets Manager with new token
    
    Args:
        user: User data from DynamoDB
        client_id: Spotify app client ID
        client_secret: Spotify app client secret
        
    Returns:
        True if token was refreshed, False if skipped (not needed yet)
        
    Raises:
        SpotifyAuthenticationError: If token refresh fails
        SecretsManagerError: If secret operations fail
    """
    user_id = user.get('userId')
    token_secret_arn = user.get('spotify_token_secret_arn')
    
    if not token_secret_arn:
        logger.warning(
            f"User {user_id} has no token secret ARN",
            extra={"user_id": user_id}
        )
        raise ValueError(f"User {user_id} missing spotify_token_secret_arn")
    
    try:
        # Get user's Spotify tokens from Secrets Manager
        logger.debug(f"Retrieving tokens for user {user_id}")
        secrets_helper = SecretsHelper()
        tokens = secrets_helper.get_secret(token_secret_arn)
        
        refresh_token = tokens.get('refresh_token')
        expires_at_str = tokens.get('expires_at')
        
        if not refresh_token:
            raise ValueError(f"User {user_id} missing refresh_token in secret")
        
        # Check if token needs refresh
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                time_until_expiry = expires_at - datetime.utcnow()
                
                # Skip if token is still valid for more than buffer time
                if time_until_expiry.total_seconds() > (TOKEN_REFRESH_BUFFER_MINUTES * 60):
                    logger.debug(
                        f"Token for user {user_id} still valid for {time_until_expiry.total_seconds():.0f}s, skipping refresh",
                        extra={
                            "user_id": user_id,
                            "expires_in_seconds": time_until_expiry.total_seconds()
                        }
                    )
                    return False
                    
            except (ValueError, AttributeError) as e:
                logger.warning(
                    f"Could not parse expires_at for user {user_id}, will refresh anyway: {e}",
                    extra={"user_id": user_id}
                )
        
        # Refresh the token
        logger.info(f"Refreshing token for user {user_id}")
        spotify_client = SpotifyClient()
        
        new_tokens = spotify_client.refresh_token(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Update tokens in secret (merge with existing data)
        updated_token_data = {
            **tokens,  # Keep existing fields
            'access_token': new_tokens['access_token'],
            'expires_at': new_tokens['expires_at'],
            'token_type': new_tokens.get('token_type', 'Bearer'),
            'scope': new_tokens.get('scope', tokens.get('scope', '')),
            'refresh_token': refresh_token,  # Keep same refresh token
            'last_refreshed': datetime.utcnow().isoformat()
        }
        
        # Update secret
        logger.debug(f"Updating secret for user {user_id}")
        secrets_helper.update_secret(token_secret_arn, updated_token_data)
        
        logger.info(
            f"Successfully refreshed and updated token for user {user_id}",
            extra={
                "user_id": user_id,
                "new_expires_at": new_tokens['expires_at']
            }
        )
        
        return True
        
    except SpotifyAuthenticationError as e:
        logger.error(
            f"Spotify authentication failed for user {user_id}",
            extra={"user_id": user_id, "error": str(e)}
        )
        raise
        
    except SecretsManagerError as e:
        logger.error(
            f"Secrets Manager error for user {user_id}",
            extra={"user_id": user_id, "error": str(e)}
        )
        raise
        
    except Exception as e:
        logger.error(
            f"Unexpected error refreshing token for user {user_id}: {str(e)}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise
