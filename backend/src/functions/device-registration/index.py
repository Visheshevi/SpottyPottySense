"""
Device Registration Lambda Function

Provisions and deprovisions IoT sensors.

REGISTRATION Flow:
1. Validate input (sensorId, location, userId)
2. Check if sensorId already exists (prevent duplicates)
3. Create IoT Thing in AWS IoT Core
4. Generate X.509 certificate and private key
5. Attach certificate to Thing
6. Attach IoT Policy to certificate
7. Create sensor record in DynamoDB
8. Return certificate, private key, and connection info (ONE TIME)

DEREGISTRATION Flow:
1. Validate input (sensorId)
2. Get sensor record from DynamoDB
3. List principals attached to Thing
4. Detach policy from each certificate
5. Detach certificates from Thing
6. Delete certificates
7. Delete IoT Thing
8. Delete sensor record from DynamoDB

⚠️ SECURITY CRITICAL: This function returns certificates and private keys ONE TIME ONLY.
Users MUST save these credentials immediately as they cannot be retrieved later.

Environment Variables:
- SENSORS_TABLE: DynamoDB Sensors table name
- IOT_POLICY_NAME: IoT policy name to attach
- AWS_REGION: AWS region (auto-set by Lambda)
- LOG_LEVEL: Logging level

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2.6)
"""

import os
import json
import time
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from logger import get_logger, log_error, log_performance, add_persistent_context
from dynamodb_helper import DynamoDBHelper
from exceptions import (
    ValidationError,
    ResourceNotFoundError,
    ConfigurationError
)

logger = get_logger(__name__)

# Initialize AWS clients
iot_client = boto3.client('iot')

# Environment variables
SENSORS_TABLE = os.environ.get('SENSORS_TABLE')
IOT_POLICY_NAME = os.environ.get('IOT_POLICY_NAME')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')


def handler(event, context):
    """
    Lambda handler for device registration and deregistration.
    
    Supports two operations:
    - register: Provision new IoT sensor with certificates
    - deregister: Clean up IoT sensor and remove from system
    
    Args:
        event: Operation request with action and parameters
        context: Lambda context object
        
    Returns:
        dict: Operation result
        
    Example Register Request:
        {
            "action": "register",
            "sensorId": "bathroom-main",
            "location": "Main Bathroom",
            "userId": "user-123"
        }
        
    Example Deregister Request:
        {
            "action": "deregister",
            "sensorId": "bathroom-main"
        }
    """
    start_time = time.time()
    
    logger.info(
        "Device Management invoked",
        extra={
            "function_name": context.function_name,
            "request_id": context.aws_request_id
        }
    )
    
    try:
        # Validate environment
        validate_environment()
        
        # Parse request body
        body = parse_request_body(event)
        
        # Get action (default to 'register' for backward compatibility)
        action = body.get('action', 'register')
        
        logger.info(f"Processing action: {action}")
        
        # Route to appropriate handler
        if action == 'register':
            response_body = handle_registration(body)
        elif action == 'deregister':
            response_body = handle_deregistration(body)
        else:
            raise ValidationError(
                message=f"Unknown action: {action}. Must be 'register' or 'deregister'",
                field="action"
            )
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        response_body['duration_ms'] = round(duration_ms, 2)
        response_body['timestamp'] = datetime.utcnow().isoformat()
        
        # Log performance
        log_performance(
            logger,
            f"device_{action}_complete",
            duration_ms,
            success=True
        )
        
        return format_response(event, 200, response_body)
        
    except ValidationError as e:
        log_error(logger, e, "Validation error")
        return format_response(event, 400, {
            'error': 'ValidationError',
            'message': str(e)
        })
        
    except ResourceNotFoundError as e:
        log_error(logger, e, "Resource not found")
        return format_response(event, 404, {
            'error': 'ResourceNotFoundError',
            'message': str(e)
        })
        
    except Exception as e:
        log_error(logger, e, "Unexpected error")
        return format_response(event, 500, {
            'error': 'InternalError',
            'message': str(e)
        })


# ==============================================================================
# OPERATION HANDLERS
# ==============================================================================

def handle_registration(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle device registration operation.
    
    Args:
        body: Request body with sensor details
        
    Returns:
        Registration response with certificates
    """
    # Extract and validate input
    sensor_id = body.get('sensorId')
    location = body.get('location')
    user_id = body.get('userId')
    
    validate_input(sensor_id, location, user_id)
    
    add_persistent_context(logger, sensor_id=sensor_id, user_id=user_id)
    
    logger.info(
        f"Registering device: {sensor_id}",
        extra={"location": location, "user_id": user_id}
    )
    
    # Check if sensor already exists
    check_sensor_exists(sensor_id)
    
    # Create IoT Thing
    thing_name, thing_arn = create_iot_thing(sensor_id, location, user_id)
    
    # Generate certificate and keys
    cert_arn, cert_pem, private_key, cert_id = create_certificate()
    
    # Attach certificate to Thing
    attach_certificate_to_thing(thing_name, cert_arn)
    
    # Attach IoT Policy to certificate
    attach_policy_to_certificate(cert_arn)
    
    # Get IoT endpoint
    iot_endpoint = get_iot_endpoint()
    
    # Create sensor record in DynamoDB
    create_sensor_record(
        sensor_id=sensor_id,
        user_id=user_id,
        location=location,
        thing_name=thing_name,
        thing_arn=thing_arn,
        cert_id=cert_id,
        cert_arn=cert_arn,
        body=body
    )
    
    # Build response with ONE-TIME credentials
    response_body = {
        'action': 'register',
        'sensorId': sensor_id,
        'location': location,
        'thingName': thing_name,
        'thingArn': thing_arn,
        'certificateArn': cert_arn,
        'certificateId': cert_id,
        'certificatePem': cert_pem,
        'privateKey': private_key,
        'iotEndpoint': iot_endpoint,
        'iotPolicyName': IOT_POLICY_NAME,
        'region': AWS_REGION,
        'mqttTopics': {
            'motion': f'sensors/{sensor_id}/motion',
            'register': f'sensors/{sensor_id}/register',
            'status': f'sensors/{sensor_id}/status'
        },
        'warning': '⚠️ SAVE CERTIFICATE AND PRIVATE KEY NOW - THEY WILL NOT BE SHOWN AGAIN!',
        'message': f'Device {sensor_id} registered successfully'
    }
    
    logger.info(
        "Device registration completed successfully",
        extra={"sensor_id": sensor_id, "thing_name": thing_name}
    )
    
    return response_body


def handle_deregistration(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle device deregistration operation.
    
    Cleans up ALL AWS resources associated with the sensor:
    - Detaches and deletes certificates
    - Deletes IoT Thing
    - Removes DynamoDB record
    
    Args:
        body: Request body with sensorId
        
    Returns:
        Deregistration response
    """
    sensor_id = body.get('sensorId')
    
    if not sensor_id:
        raise ValidationError(message="sensorId is required", field="sensorId")
    
    add_persistent_context(logger, sensor_id=sensor_id)
    
    logger.info(f"Deregistering device: {sensor_id}")
    
    # Get sensor record
    sensor = get_sensor_record(sensor_id)
    thing_name = sensor.get('thingName')
    
    if not thing_name:
        thing_name = f"SpottyPottySense-{sensor_id}"
    
    # Track cleanup operations
    cleanup_summary = {
        'certificates_detached': 0,
        'certificates_deleted': 0,
        'thing_deleted': False,
        'dynamodb_deleted': False
    }
    
    # Step 1: List and clean up certificates
    try:
        principals = list_thing_principals(thing_name)
        
        for principal in principals:
            cert_arn = principal
            cert_id = extract_cert_id_from_arn(cert_arn)
            
            # Detach policy from certificate
            detach_policy_from_certificate(cert_arn)
            
            # Detach certificate from Thing
            detach_certificate_from_thing(thing_name, cert_arn)
            cleanup_summary['certificates_detached'] += 1
            
            # Deactivate and delete certificate
            deactivate_certificate(cert_id)
            delete_certificate(cert_id)
            cleanup_summary['certificates_deleted'] += 1
            
    except Exception as e:
        logger.warning(f"Error cleaning up certificates: {e}")
    
    # Step 2: Delete IoT Thing
    try:
        delete_thing(thing_name)
        cleanup_summary['thing_deleted'] = True
    except Exception as e:
        logger.warning(f"Error deleting Thing: {e}")
    
    # Step 3: Delete sensor from DynamoDB
    try:
        delete_sensor_record(sensor_id)
        cleanup_summary['dynamodb_deleted'] = True
    except Exception as e:
        logger.error(f"Failed to delete sensor from DynamoDB: {e}")
        raise
    
    response_body = {
        'action': 'deregister',
        'sensorId': sensor_id,
        'thingName': thing_name,
        'message': f'Device {sensor_id} deregistered successfully',
        'cleanup': cleanup_summary
    }
    
    logger.info(
        "Device deregistration completed",
        extra={"sensor_id": sensor_id, "cleanup": cleanup_summary}
    )
    
    return response_body


# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

def validate_environment() -> None:
    """Validate required environment variables."""
    required = ['SENSORS_TABLE', 'IOT_POLICY_NAME']
    missing = [var for var in required if not os.environ.get(var)]
    
    if missing:
        raise ConfigurationError(
            message=f"Missing required environment variables: {', '.join(missing)}",
            details={"missing_variables": missing}
        )


def parse_request_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse request body from API Gateway or direct invocation."""
    if 'body' in event:
        # API Gateway format
        body_str = event['body']
        if isinstance(body_str, str):
            return json.loads(body_str)
        return body_str
    else:
        # Direct invocation
        return event


def validate_input(sensor_id: Optional[str], location: Optional[str], user_id: Optional[str]) -> None:
    """Validate required input fields."""
    if not sensor_id:
        raise ValidationError(message="sensorId is required", field="sensorId")
    
    if not location:
        raise ValidationError(message="location is required", field="location")
    
    if not user_id:
        raise ValidationError(message="userId is required", field="userId")
    
    # Validate sensorId format (alphanumeric, hyphens, underscores only)
    if not sensor_id.replace('-', '').replace('_', '').isalnum():
        raise ValidationError(
            message="sensorId must contain only alphanumeric characters, hyphens, and underscores",
            field="sensorId"
        )
    
    # Validate length
    if len(sensor_id) < 3 or len(sensor_id) > 128:
        raise ValidationError(
            message="sensorId must be between 3 and 128 characters",
            field="sensorId"
        )


def check_sensor_exists(sensor_id: str) -> None:
    """Check if sensor already exists in DynamoDB."""
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    existing = dynamodb.get_item({'sensorId': sensor_id})
    
    if existing:
        logger.warning(f"Sensor already exists: {sensor_id}")
        raise ValidationError(
            message=f"Sensor with ID '{sensor_id}' already exists",
            field="sensorId"
        )


# ==============================================================================
# IOT OPERATIONS
# ==============================================================================

def create_iot_thing(sensor_id: str, location: str, user_id: str) -> tuple:
    """
    Create IoT Thing in AWS IoT Core.
    
    Returns:
        Tuple of (thing_name, thing_arn)
    """
    thing_name = f"SpottyPottySense-{sensor_id}"
    
    logger.info(f"Creating IoT Thing: {thing_name}")
    
    try:
        # Create Thing without type for now (can be added later if needed)
        response = iot_client.create_thing(
            thingName=thing_name,
            attributePayload={
                'attributes': {
                    'sensorId': sensor_id,
                    'location': location.replace(' ', '_'),  # Remove spaces
                    'userId': user_id
                }
            }
        )
        
        thing_arn = response['thingArn']
        
        logger.info(f"IoT Thing created: {thing_name}", extra={"thing_arn": thing_arn})
        
        return thing_name, thing_arn
        
    except iot_client.exceptions.ResourceAlreadyExistsException:
        logger.error(f"IoT Thing already exists: {thing_name}")
        raise ValidationError(
            message=f"IoT Thing '{thing_name}' already exists",
            field="sensorId"
        )
    except Exception as e:
        logger.error(f"Failed to create IoT Thing: {e}", exc_info=True)
        raise


def create_certificate() -> tuple:
    """
    Generate X.509 certificate and private key.
    
    Returns:
        Tuple of (certificate_arn, certificate_pem, private_key, certificate_id)
    """
    logger.info("Generating X.509 certificate and keys")
    
    try:
        response = iot_client.create_keys_and_certificate(setAsActive=True)
        
        cert_arn = response['certificateArn']
        cert_id = response['certificateId']
        cert_pem = response['certificatePem']
        private_key = response['keyPair']['PrivateKey']
        
        logger.info(
            "Certificate generated",
            extra={"certificate_id": cert_id}
        )
        
        return cert_arn, cert_pem, private_key, cert_id
        
    except Exception as e:
        logger.error(f"Failed to create certificate: {e}", exc_info=True)
        raise


def attach_certificate_to_thing(thing_name: str, cert_arn: str) -> None:
    """Attach certificate to IoT Thing."""
    logger.info(f"Attaching certificate to Thing: {thing_name}")
    
    try:
        iot_client.attach_thing_principal(
            thingName=thing_name,
            principal=cert_arn
        )
        
        logger.info("Certificate attached to Thing")
        
    except Exception as e:
        logger.error(f"Failed to attach certificate to Thing: {e}", exc_info=True)
        raise


def attach_policy_to_certificate(cert_arn: str) -> None:
    """Attach IoT Policy to certificate."""
    logger.info(f"Attaching policy '{IOT_POLICY_NAME}' to certificate")
    
    try:
        iot_client.attach_policy(
            policyName=IOT_POLICY_NAME,
            target=cert_arn
        )
        
        logger.info("Policy attached to certificate")
        
    except Exception as e:
        logger.error(f"Failed to attach policy to certificate: {e}", exc_info=True)
        raise


def get_iot_endpoint() -> str:
    """Get AWS IoT Core endpoint for MQTT connection."""
    try:
        response = iot_client.describe_endpoint(endpointType='iot:Data-ATS')
        endpoint = response['endpointAddress']
        
        logger.debug(f"IoT endpoint: {endpoint}")
        
        return endpoint
        
    except Exception as e:
        logger.error(f"Failed to get IoT endpoint: {e}", exc_info=True)
        raise


# ==============================================================================
# DYNAMODB OPERATIONS
# ==============================================================================

def create_sensor_record(
    sensor_id: str,
    user_id: str,
    location: str,
    thing_name: str,
    thing_arn: str,
    cert_id: str,
    cert_arn: str,
    body: Dict[str, Any]
) -> None:
    """Create sensor record in DynamoDB."""
    logger.info("Creating sensor record in DynamoDB")
    
    now = datetime.utcnow()
    
    sensor = {
        'sensorId': sensor_id,
        'userId': user_id,
        'name': body.get('name', location),
        'location': location,
        'thingName': thing_name,
        'thingArn': thing_arn,
        'certificateId': cert_id,
        'certificateArn': cert_arn,
        'enabled': True,
        'status': 'registered',
        'createdAt': now.isoformat(),
        'updatedAt': now.isoformat()
    }
    
    # Optional fields from request
    if 'spotifyDeviceId' in body:
        sensor['spotifyDeviceId'] = body['spotifyDeviceId']
    
    if 'playlistUri' in body:
        sensor['playlistUri'] = body['playlistUri']
    
    if 'timeoutMinutes' in body:
        sensor['timeoutMinutes'] = body['timeoutMinutes']
    
    if 'motionDebounceMinutes' in body:
        sensor['motionDebounceMinutes'] = body['motionDebounceMinutes']
    
    # Quiet hours
    if 'quietHours' in body:
        sensor['quietHours'] = body['quietHours']
    
    # Save to DynamoDB
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    dynamodb.put_item(sensor)
    
    logger.info("Sensor record created in DynamoDB")


# ==============================================================================
# RESPONSE HELPERS
# ==============================================================================

def get_sensor_record(sensor_id: str) -> Dict[str, Any]:
    """Get sensor record from DynamoDB."""
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    sensor = dynamodb.get_item({'sensorId': sensor_id})
    
    if not sensor:
        raise ResourceNotFoundError(
            message=f"Sensor not found: {sensor_id}",
            resource_type="Sensor",
            resource_id=sensor_id
        )
    
    return sensor


def delete_sensor_record(sensor_id: str) -> None:
    """Delete sensor record from DynamoDB."""
    logger.info(f"Deleting sensor from DynamoDB: {sensor_id}")
    
    dynamodb = DynamoDBHelper(SENSORS_TABLE)
    dynamodb.delete_item({'sensorId': sensor_id})
    
    logger.info("Sensor record deleted")


# ==============================================================================
# IOT CLEANUP OPERATIONS
# ==============================================================================

def list_thing_principals(thing_name: str) -> list:
    """List all principals (certificates) attached to a Thing."""
    logger.info(f"Listing principals for Thing: {thing_name}")
    
    try:
        response = iot_client.list_thing_principals(thingName=thing_name)
        principals = response.get('principals', [])
        
        logger.info(f"Found {len(principals)} principals attached to Thing")
        return principals
        
    except iot_client.exceptions.ResourceNotFoundException:
        logger.warning(f"Thing not found: {thing_name}")
        return []
    except Exception as e:
        logger.error(f"Failed to list Thing principals: {e}", exc_info=True)
        raise


def extract_cert_id_from_arn(cert_arn: str) -> str:
    """Extract certificate ID from ARN."""
    # ARN format: arn:aws:iot:region:account:cert/CERT_ID
    return cert_arn.split('/')[-1]


def detach_policy_from_certificate(cert_arn: str) -> None:
    """Detach IoT Policy from certificate."""
    logger.info(f"Detaching policy from certificate")
    
    try:
        iot_client.detach_policy(
            policyName=IOT_POLICY_NAME,
            target=cert_arn
        )
        logger.info("Policy detached from certificate")
        
    except iot_client.exceptions.ResourceNotFoundException:
        logger.warning("Policy or certificate not found (already detached?)")
    except Exception as e:
        logger.error(f"Failed to detach policy: {e}", exc_info=True)
        # Don't raise - continue cleanup


def detach_certificate_from_thing(thing_name: str, cert_arn: str) -> None:
    """Detach certificate from IoT Thing."""
    logger.info(f"Detaching certificate from Thing: {thing_name}")
    
    try:
        iot_client.detach_thing_principal(
            thingName=thing_name,
            principal=cert_arn
        )
        logger.info("Certificate detached from Thing")
        
    except iot_client.exceptions.ResourceNotFoundException:
        logger.warning("Thing or certificate not found (already detached?)")
    except Exception as e:
        logger.error(f"Failed to detach certificate from Thing: {e}", exc_info=True)
        # Don't raise - continue cleanup


def deactivate_certificate(cert_id: str) -> None:
    """Deactivate certificate (required before deletion)."""
    logger.info(f"Deactivating certificate: {cert_id}")
    
    try:
        iot_client.update_certificate(
            certificateId=cert_id,
            newStatus='INACTIVE'
        )
        logger.info("Certificate deactivated")
        
    except Exception as e:
        logger.error(f"Failed to deactivate certificate: {e}", exc_info=True)
        # Don't raise - continue cleanup


def delete_certificate(cert_id: str) -> None:
    """Delete certificate from IoT Core."""
    logger.info(f"Deleting certificate: {cert_id}")
    
    try:
        iot_client.delete_certificate(certificateId=cert_id)
        logger.info("Certificate deleted")
        
    except Exception as e:
        logger.error(f"Failed to delete certificate: {e}", exc_info=True)
        # Don't raise - continue cleanup


def delete_thing(thing_name: str) -> None:
    """Delete IoT Thing."""
    logger.info(f"Deleting Thing: {thing_name}")
    
    try:
        iot_client.delete_thing(thingName=thing_name)
        logger.info("Thing deleted")
        
    except iot_client.exceptions.ResourceNotFoundException:
        logger.warning(f"Thing not found: {thing_name} (already deleted?)")
    except Exception as e:
        logger.error(f"Failed to delete Thing: {e}", exc_info=True)
        raise


# ==============================================================================
# RESPONSE HELPERS
# ==============================================================================

def format_response(event: Dict[str, Any], status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Format response for API Gateway or direct invocation."""
    if 'body' in event:
        # API Gateway format
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,DELETE,OPTIONS'
            },
            'body': json.dumps(body)
        }
    else:
        # Direct invocation format
        return {
            'statusCode': status_code,
            **body
        }
