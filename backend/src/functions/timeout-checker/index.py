"""
Timeout Checker Function
Check for inactive sessions and automatically stop Spotify playback.

This is a STUB implementation for Phase 1 deployment.
Full implementation will be added in Phase 2.
"""

import json
import os
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


def handler(event, context):
    """
    Lambda handler for checking session timeouts.
    Triggered by EventBridge every minute.
    
    Args:
        event: EventBridge scheduled event
        context: Lambda context object
        
    Returns:
        dict: Summary of timeout checking operations
    """
    logger.info("Timeout Checker invoked", extra={
        "event": event,
        "function_name": context.function_name,
        "request_id": context.aws_request_id
    })
    
    try:
        logger.info("Starting session timeout check")
        
        # STUB: In Phase 2, we will:
        # 1. Query active sessions from DynamoDB (status='active')
        # 2. For each active session:
        #    - Get sensor configuration (timeoutMinutes)
        #    - Calculate elapsed time since lastMotionTime
        #    - If elapsed > timeout:
        #      * Get Spotify access token
        #      * Call Spotify API to pause playback
        #      * Update session status to 'completed'
        #      * Calculate and save session statistics
        # 3. Clean up old completed sessions (TTL handles this automatically)
        
        # For now, just return success
        response = {
            'statusCode': 200,
            'timestamp': datetime.now().isoformat(),
            'activeSessionsChecked': 0,
            'sessionsTimedOut': 0,
            'playbacksStopped': 0,
            'message': 'STUB: Timeout check scheduled task executed',
            'note': 'Full implementation will be added in Phase 2'
        }
        
        logger.info("Timeout check completed", extra=response)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in timeout check: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'error': 'InternalError',
            'message': str(e)
        }

