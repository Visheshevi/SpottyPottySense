"""
Device Registration Function
Provision new IoT sensors - create Thing, generate certificates, attach policies.

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
    Lambda handler for device registration/provisioning.
    Called via API Gateway or IoT Rule.
    
    Args:
        event: Registration request with sensor details
        context: Lambda context object
        
    Returns:
        dict: Registration result with certificates (ONE TIME ONLY)
    """
    logger.info("Device Registration invoked", extra={
        "event": event,
        "function_name": context.function_name,
        "request_id": context.request_id
    })
    
    try:
        # Parse request body if from API Gateway
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        sensor_id = body.get('sensorId', 'unknown')
        location = body.get('location', 'Unknown Location')
        user_id = body.get('userId', 'unknown')
        
        logger.info(f"Registering device: {sensor_id} at {location}")
        
        # STUB: In Phase 2, we will:
        # 1. Validate input (sensorId, location, userId)
        # 2. Check if sensorId already exists
        # 3. Create IoT Thing in AWS IoT Core
        # 4. Generate X.509 certificate and private key
        # 5. Attach certificate to Thing
        # 6. Attach IoT Policy to certificate
        # 7. Create sensor record in DynamoDB
        # 8. Return certificate and endpoint info (ONE TIME ONLY - user must save!)
        
        # For now, return stub response
        response_body = {
            'sensorId': sensor_id,
            'location': location,
            'thingArn': f'arn:aws:iot:us-east-1:123456789012:thing/sensor-{sensor_id}',
            'certificateArn': 'arn:aws:iot:us-east-1:123456789012:cert/stub-certificate',
            'certificatePem': 'STUB_CERTIFICATE_PEM_CONTENT',
            'privateKey': 'STUB_PRIVATE_KEY_CONTENT',
            'iotEndpoint': 'stub.iot.us-east-1.amazonaws.com',
            'message': 'STUB: Device registration successful',
            'warning': '⚠️  Save certificate and private key NOW - they will not be shown again!',
            'note': 'Full implementation will be added in Phase 2'
        }
        
        # Format response for API Gateway if needed
        if 'body' in event:
            response = {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(response_body)
            }
        else:
            response = {
                'statusCode': 200,
                **response_body
            }
        
        logger.info("Device registration completed", extra={
            "sensor_id": sensor_id,
            "location": location
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Error in device registration: {str(e)}", exc_info=True)
        
        error_body = {
            'error': 'InternalError',
            'message': str(e)
        }
        
        if 'body' in event:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(error_body)
            }
        else:
            return {
                'statusCode': 500,
                **error_body
            }

