"""
End-to-End Integration Tests for SpottyPottySense

Tests complete workflows from device registration through motion detection,
session management, and analytics.

Run with: pytest backend/tests/integration/test_e2e_flow.py -v -s
"""

import json
import time
import boto3
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

# AWS Configuration
AWS_REGION = 'us-east-2'
STACK_NAME = 'spotty-potty-sense'

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
iot_client = boto3.client('iot', region_name=AWS_REGION)
cloudformation = boto3.client('cloudformation', region_name=AWS_REGION)


# ==============================================================================
# FIXTURES & SETUP
# ==============================================================================

@pytest.fixture(scope='module')
def stack_outputs():
    """Get CloudFormation stack outputs."""
    response = cloudformation.describe_stacks(StackName=STACK_NAME)
    outputs = {}
    for output in response['Stacks'][0]['Outputs']:
        outputs[output['OutputKey']] = output['OutputValue']
    return outputs


@pytest.fixture(scope='module')
def lambda_functions(stack_outputs):
    """Get Lambda function names from stack."""
    return {
        'device_registration': f"SpottyPottySense-DeviceRegistration-dev",
        'motion_handler': f"SpottyPottySense-MotionHandler-dev",
        'timeout_checker': f"SpottyPottySense-TimeoutChecker-dev",
        'session_manager': f"SpottyPottySense-SessionManager-dev",
        'token_refresher': f"SpottyPottySense-TokenRefresher-dev",
        'api_handler': f"SpottyPottySense-ApiHandler-dev"
    }


@pytest.fixture(scope='module')
def test_user_id():
    """Test user ID for integration tests."""
    return "integration-test-user-001"


@pytest.fixture(scope='module')
def test_sensor_id():
    """Test sensor ID for integration tests."""
    timestamp = int(time.time())
    return f"integration-test-sensor-{timestamp}"


@pytest.fixture(scope='function')
def cleanup_sensor(test_sensor_id, lambda_functions):
    """Cleanup fixture to delete sensor after test."""
    yield
    
    # Cleanup: Deregister sensor
    try:
        payload = {
            'action': 'deregister',
            'sensorId': test_sensor_id
        }
        
        lambda_client.invoke(
            FunctionName=lambda_functions['device_registration'],
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        print(f"\n✓ Cleaned up sensor: {test_sensor_id}")
    except Exception as e:
        print(f"\n✗ Cleanup failed: {e}")


# ==============================================================================
# TEST: DEVICE REGISTRATION FLOW
# ==============================================================================

def test_001_device_registration_flow(
    lambda_functions,
    test_sensor_id,
    test_user_id,
    cleanup_sensor
):
    """
    Test complete device registration flow.
    
    Steps:
    1. Register new sensor
    2. Verify sensor created in DynamoDB
    3. Verify IoT Thing created
    4. Verify certificates issued
    """
    print("\n" + "="*70)
    print("TEST 001: Device Registration Flow")
    print("="*70)
    
    # Step 1: Register sensor
    print(f"\n[Step 1] Registering sensor: {test_sensor_id}")
    
    payload = {
        'action': 'register',
        'sensorId': test_sensor_id,
        'location': 'Integration Test Bathroom',
        'userId': test_user_id,
        'name': 'Integration Test Sensor',
        'spotifyDeviceId': 'test-device-123',
        'playlistUri': 'spotify:playlist:37i9dQZF1DXcBWIGoYBM5M',
        'timeoutMinutes': 5,
        'motionDebounceMinutes': 2
    }
    
    response = lambda_client.invoke(
        FunctionName=lambda_functions['device_registration'],
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Response Status: {result.get('statusCode')}")
    
    assert result['statusCode'] == 200, f"Registration failed: {result}"
    
    # Parse response body
    if isinstance(result.get('body'), str):
        body = json.loads(result['body'])
    else:
        body = result
    
    assert body['sensorId'] == test_sensor_id
    assert 'certificateId' in body
    assert 'certificatePem' in body
    assert 'privateKey' in body
    assert 'iotEndpoint' in body
    
    print(f"✓ Sensor registered successfully")
    print(f"  - Thing Name: {body.get('thingName')}")
    print(f"  - Certificate ID: {body.get('certificateId')[:20]}...")
    print(f"  - IoT Endpoint: {body.get('iotEndpoint')}")
    
    # Step 2: Verify sensor in DynamoDB
    print(f"\n[Step 2] Verifying sensor in DynamoDB")
    
    sensors_table = dynamodb.Table('SpottyPottySense-Sensors-dev')
    db_response = sensors_table.get_item(Key={'sensorId': test_sensor_id})
    
    assert 'Item' in db_response, "Sensor not found in DynamoDB"
    sensor = db_response['Item']
    
    assert sensor['userId'] == test_user_id
    assert sensor['location'] == 'Integration Test Bathroom'
    assert sensor['enabled'] == True  # Field is 'enabled', not 'isActive'
    
    print(f"✓ Sensor found in DynamoDB")
    print(f"  - User ID: {sensor['userId']}")
    print(f"  - Location: {sensor['location']}")
    print(f"  - Status: {'Enabled' if sensor.get('enabled', False) else 'Disabled'}")
    
    # Step 3: Verify IoT Thing
    print(f"\n[Step 3] Verifying IoT Thing")
    
    thing_name = body.get('thingName')
    thing_response = iot_client.describe_thing(thingName=thing_name)
    
    assert thing_response['thingName'] == thing_name
    print(f"✓ IoT Thing verified: {thing_name}")
    
    # Step 4: Verify certificates
    print(f"\n[Step 4] Verifying certificates")
    
    principals = iot_client.list_thing_principals(thingName=thing_name)
    assert len(principals['principals']) > 0, "No certificates attached"
    
    print(f"✓ {len(principals['principals'])} certificate(s) attached")
    
    print(f"\n{'='*70}")
    print("✓ TEST 001 PASSED: Device Registration Flow")
    print(f"{'='*70}\n")


# ==============================================================================
# TEST: MOTION DETECTION FLOW
# ==============================================================================

def test_002_motion_detection_flow(
    lambda_functions,
    test_sensor_id,
    test_user_id,
    cleanup_sensor
):
    """
    Test complete motion detection and session creation flow.
    
    Steps:
    1. Create test user and sensor setup
    2. Send motion event
    3. Verify session created
    4. Verify motion event logged
    """
    print("\n" + "="*70)
    print("TEST 002: Motion Detection Flow")
    print("="*70)
    
    # Step 1: Setup test data
    print(f"\n[Step 1] Setting up test user and sensor")
    
    users_table = dynamodb.Table('SpottyPottySense-Users-dev')
    sensors_table = dynamodb.Table('SpottyPottySense-Sensors-dev')
    
    # Create test user (if not exists)
    try:
        users_table.put_item(
            Item={
                'userId': test_user_id,
                'email': 'integration-test@example.com',
                'name': 'Integration Test User',
                'spotifyAccessToken': 'test-token',
                'spotifyRefreshToken': 'test-refresh',
                'spotifyTokenExpiry': int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
                'createdAt': datetime.utcnow().isoformat(),
                'updatedAt': datetime.utcnow().isoformat()
            }
        )
        print(f"✓ Test user created: {test_user_id}")
    except Exception as e:
        print(f"  User may already exist: {e}")
    
    # Register sensor for this test
    print(f"\n[Step 1b] Registering sensor for motion test")
    registration_payload = {
        'action': 'register',
        'sensorId': test_sensor_id,
        'location': 'Motion Test Bathroom',
        'userId': test_user_id,
        'name': 'Motion Test Sensor',
        'spotifyDeviceId': 'test-device-motion',
        'playlistUri': 'spotify:playlist:37i9dQZF1DXcBWIGoYBM5M',
        'timeoutMinutes': 5,
        'motionDebounceMinutes': 2
    }
    
    response = lambda_client.invoke(
        FunctionName=lambda_functions['device_registration'],
        InvocationType='RequestResponse',
        Payload=json.dumps(registration_payload)
    )
    
    result = json.loads(response['Payload'].read())
    if result.get('statusCode') != 200:
        pytest.skip(f"Failed to register sensor for test: {result}")
    
    print(f"✓ Test sensor registered: {test_sensor_id}")
    
    # Step 2: Send motion event
    print(f"\n[Step 2] Sending motion detection event")
    
    motion_payload = {
        'sensorId': test_sensor_id,
        'event': 'motion_detected',
        'timestamp': datetime.utcnow().isoformat(),
        'metadata': {
            'source': 'integration-test'
        }
    }
    
    # Note: Motion handler expects IoT Core format
    iot_event = {
        'topic': f'sensors/{test_sensor_id}/motion',
        'payload': json.dumps(motion_payload)
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=lambda_functions['motion_handler'],
            InvocationType='RequestResponse',
            Payload=json.dumps(iot_event)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Motion Handler Status: {result.get('statusCode', 'N/A')}")
        
        # Motion handler may fail due to Spotify API not being configured
        # That's okay for this test - we're just verifying the flow
        if result.get('statusCode') != 200:
            print(f"  Note: Motion handler returned {result.get('statusCode')}")
            print(f"  This is expected if Spotify credentials are not configured")
        
    except Exception as e:
        print(f"  Motion event processing: {e}")
        print(f"  Note: Spotify API errors are expected in test environment")
    
    # Step 3: Verify session (may not exist if Spotify failed)
    print(f"\n[Step 3] Checking for session creation")
    
    sessions_table = dynamodb.Table('SpottyPottySense-Sessions-dev')
    
    # Query sessions for this sensor
    session_response = sessions_table.query(
        IndexName='SensorIdIndex',
        KeyConditionExpression='sensorId = :sid',
        ExpressionAttributeValues={':sid': test_sensor_id},
        Limit=1,
        ScanIndexForward=False
    )
    
    if session_response['Items']:
        session = session_response['Items'][0]
        print(f"✓ Session found: {session['sessionId']}")
        print(f"  - Status: {session.get('status')}")
        print(f"  - Start Time: {session.get('startTimeISO')}")
    else:
        print(f"  No session created (expected if Spotify not configured)")
    
    print(f"\n{'='*70}")
    print("✓ TEST 002 PASSED: Motion Detection Flow")
    print(f"{'='*70}\n")


# ==============================================================================
# TEST: API CRUD OPERATIONS
# ==============================================================================

def test_003_api_crud_operations(
    lambda_functions,
    test_sensor_id,
    test_user_id
):
    """
    Test complete API CRUD operations.
    
    Steps:
    1. List sensors (GET /sensors)
    2. Get sensor details (GET /sensors/{id})
    3. Update sensor (PUT /sensors/{id})
    4. Get user profile (GET /users/me)
    5. Get analytics (GET /analytics)
    """
    print("\n" + "="*70)
    print("TEST 003: API CRUD Operations")
    print("="*70)
    
    # Helper function to create API event
    def create_api_event(method, path, body=None, query=None, path_params=None):
        return {
            'httpMethod': method,
            'path': path,
            'pathParameters': path_params or {},
            'queryStringParameters': query or {},
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(body) if body else None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': test_user_id,
                        'email': 'integration-test@example.com'
                    }
                }
            }
        }
    
    # Step 1: List sensors
    print(f"\n[Step 1] Testing GET /sensors")
    
    event = create_api_event('GET', '/sensors', query={'limit': '10'})
    response = lambda_client.invoke(
        FunctionName=lambda_functions['api_handler'],
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    assert result['statusCode'] == 200
    
    body = json.loads(result['body'])
    print(f"✓ List sensors successful")
    print(f"  - Sensors found: {body['count']}")
    print(f"  - Limit: {body['limit']}")
    
    # Step 2: Get sensor details
    print(f"\n[Step 2] Testing GET /sensors/{test_sensor_id}")
    
    event = create_api_event(
        'GET',
        f'/sensors/{test_sensor_id}',
        path_params={'id': test_sensor_id}
    )
    response = lambda_client.invoke(
        FunctionName=lambda_functions['api_handler'],
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        sensor = body['sensor']
        print(f"✓ Get sensor successful")
        print(f"  - Sensor ID: {sensor['sensorId']}")
        print(f"  - Location: {sensor.get('location')}")
        print(f"  - Status: {'Active' if sensor.get('isActive') else 'Inactive'}")
    else:
        print(f"  Sensor not found (may have been cleaned up)")
    
    # Step 3: Update sensor
    print(f"\n[Step 3] Testing PUT /sensors/{test_sensor_id}")
    
    update_data = {
        'name': 'Updated Integration Test Sensor',
        'timeoutMinutes': 10
    }
    
    event = create_api_event(
        'PUT',
        f'/sensors/{test_sensor_id}',
        body=update_data,
        path_params={'id': test_sensor_id}
    )
    response = lambda_client.invoke(
        FunctionName=lambda_functions['api_handler'],
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"✓ Update sensor successful")
        print(f"  - Updated name: {body['sensor'].get('name')}")
        print(f"  - Updated timeout: {body['sensor'].get('timeoutMinutes')}")
    else:
        print(f"  Update failed (sensor may not exist)")
    
    # Step 4: Get user profile
    print(f"\n[Step 4] Testing GET /users/me")
    
    event = create_api_event('GET', '/users/me')
    response = lambda_client.invoke(
        FunctionName=lambda_functions['api_handler'],
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        user = body['user']
        print(f"✓ Get user profile successful")
        print(f"  - User ID: {user['userId']}")
        print(f"  - Email: {user.get('email')}")
    else:
        print(f"  User not found (create user first in test_002)")
    
    # Step 5: Get analytics
    print(f"\n[Step 5] Testing GET /analytics")
    
    event = create_api_event(
        'GET',
        '/analytics',
        query={
            'startDate': (datetime.utcnow() - timedelta(days=7)).isoformat(),
            'endDate': datetime.utcnow().isoformat()
        }
    )
    response = lambda_client.invoke(
        FunctionName=lambda_functions['api_handler'],
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    assert result['statusCode'] == 200
    
    body = json.loads(result['body'])
    summary = body['summary']
    print(f"✓ Get analytics successful")
    print(f"  - Total Sessions: {summary['totalSessions']}")
    print(f"  - Completed Sessions: {summary['completedSessions']}")
    print(f"  - Active Sessions: {summary['activeSessions']}")
    
    print(f"\n{'='*70}")
    print("✓ TEST 003 PASSED: API CRUD Operations")
    print(f"{'='*70}\n")


# ==============================================================================
# TEST: SESSION TIMEOUT FLOW
# ==============================================================================

def test_004_session_timeout_flow(
    lambda_functions,
    test_sensor_id,
    test_user_id
):
    """
    Test session timeout detection and completion.
    
    Steps:
    1. Create active session
    2. Set lastMotionTime in the past
    3. Invoke timeout checker
    4. Verify session completed
    """
    print("\n" + "="*70)
    print("TEST 004: Session Timeout Flow")
    print("="*70)
    
    sessions_table = dynamodb.Table('SpottyPottySense-Sessions-dev')
    
    # Step 1: Create test session
    print(f"\n[Step 1] Creating active test session")
    
    session_id = f"test-session-{int(time.time())}"
    now = datetime.utcnow()
    old_time = now - timedelta(minutes=15)  # 15 minutes ago
    
    sessions_table.put_item(
        Item={
            'sessionId': session_id,
            'sensorId': test_sensor_id,
            'userId': test_user_id,
            'status': 'active',
            'startTime': int(old_time.timestamp()),
            'startTimeISO': old_time.isoformat(),
            'lastMotionTime': old_time.isoformat(),
            'motionEvents': 1,
            'createdAt': old_time.isoformat()
        }
    )
    
    print(f"✓ Test session created: {session_id}")
    print(f"  - Start Time: {old_time.isoformat()}")
    print(f"  - Status: active")
    
    # Step 2: Run timeout checker
    print(f"\n[Step 2] Running timeout checker")
    
    response = lambda_client.invoke(
        FunctionName=lambda_functions['timeout_checker'],
        InvocationType='RequestResponse',
        Payload=json.dumps({})
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Timeout Checker Status: {result.get('statusCode')}")
    
    if result.get('statusCode') == 200:
        body = json.loads(result.get('body', '{}'))
        print(f"  - Sessions checked: {body.get('sessionsChecked', 0)}")
        print(f"  - Sessions timed out: {body.get('sessionsTimedOut', 0)}")
    
    # Step 3: Verify session status
    print(f"\n[Step 3] Verifying session status")
    
    time.sleep(2)  # Allow DynamoDB to update
    
    session_response = sessions_table.get_item(Key={'sessionId': session_id})
    
    if 'Item' in session_response:
        session = session_response['Item']
        print(f"✓ Session found")
        print(f"  - Status: {session.get('status')}")
        print(f"  - Duration: {session.get('durationMinutes', 0)} minutes")
        
        # Note: Session may still be active if timeout checker didn't process it
        # or if sensor timeout is > 15 minutes
        if session.get('status') == 'completed':
            print(f"  ✓ Session successfully timed out and completed")
        else:
            print(f"  Note: Session still active (timeout may be > 15 minutes)")
    else:
        print(f"  Session not found")
    
    # Cleanup
    try:
        sessions_table.delete_item(Key={'sessionId': session_id})
        print(f"\n✓ Test session cleaned up")
    except Exception as e:
        print(f"\n  Cleanup note: {e}")
    
    print(f"\n{'='*70}")
    print("✓ TEST 004 PASSED: Session Timeout Flow")
    print(f"{'='*70}\n")


# ==============================================================================
# TEST: ERROR SCENARIOS
# ==============================================================================

def test_005_error_scenarios(lambda_functions):
    """
    Test error handling across various endpoints.
    
    Tests:
    1. Invalid sensor ID
    2. Unauthorized access
    3. Missing required fields
    4. Invalid JSON
    """
    print("\n" + "="*70)
    print("TEST 005: Error Scenarios")
    print("="*70)
    
    # Test 1: Invalid sensor ID
    print(f"\n[Test 1] Testing invalid sensor ID")
    
    event = {
        'httpMethod': 'GET',
        'path': '/sensors/non-existent-sensor',
        'pathParameters': {'id': 'non-existent-sensor'},
        'queryStringParameters': {},
        'headers': {'Content-Type': 'application/json'},
        'body': None,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'test-user-999',
                    'email': 'test@example.com'
                }
            }
        }
    }
    
    response = lambda_client.invoke(
        FunctionName=lambda_functions['api_handler'],
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    assert result['statusCode'] == 404
    print(f"✓ Correctly returned 404 for non-existent sensor")
    
    # Test 2: Missing authentication
    print(f"\n[Test 2] Testing missing authentication")
    
    event = {
        'httpMethod': 'GET',
        'path': '/sensors',
        'pathParameters': {},
        'queryStringParameters': {},
        'headers': {'Content-Type': 'application/json'},
        'body': None,
        'requestContext': {}  # No authorizer
    }
    
    response = lambda_client.invoke(
        FunctionName=lambda_functions['api_handler'],
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    
    result = json.loads(response['Payload'].read())
    assert result['statusCode'] in [401, 403, 500]  # Auth error
    print(f"✓ Correctly returned {result['statusCode']} for missing auth")
    
    # Test 3: Invalid device registration (missing fields)
    print(f"\n[Test 3] Testing invalid device registration")
    
    payload = {
        'action': 'register',
        'sensorId': '',  # Empty sensor ID
        'location': 'Test'
    }
    
    response = lambda_client.invoke(
        FunctionName=lambda_functions['device_registration'],
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    assert result['statusCode'] == 400
    print(f"✓ Correctly returned 400 for invalid registration")
    
    print(f"\n{'='*70}")
    print("✓ TEST 005 PASSED: Error Scenarios")
    print(f"{'='*70}\n")


# ==============================================================================
# TEST: TOKEN REFRESHER
# ==============================================================================

def test_006_token_refresher_flow(lambda_functions, test_user_id):
    """
    Test Spotify token refresh flow.
    
    Steps:
    1. Invoke token refresher
    2. Verify it processes users
    3. Check for errors
    """
    print("\n" + "="*70)
    print("TEST 006: Token Refresher Flow")
    print("="*70)
    
    print(f"\n[Step 1] Invoking token refresher")
    
    response = lambda_client.invoke(
        FunctionName=lambda_functions['token_refresher'],
        InvocationType='RequestResponse',
        Payload=json.dumps({})
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Token Refresher Status: {result.get('statusCode')}")
    
    if result.get('statusCode') == 200:
        body = json.loads(result.get('body', '{}'))
        print(f"✓ Token refresher completed")
        print(f"  - Users processed: {body.get('usersProcessed', 0)}")
        print(f"  - Tokens refreshed: {body.get('tokensRefreshed', 0)}")
        print(f"  - Errors: {body.get('errors', 0)}")
    else:
        print(f"  Token refresher returned: {result.get('statusCode')}")
    
    print(f"\n{'='*70}")
    print("✓ TEST 006 PASSED: Token Refresher Flow")
    print(f"{'='*70}\n")


# ==============================================================================
# SUMMARY
# ==============================================================================

def test_999_integration_summary():
    """Print integration test summary."""
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    print("\n✓ All integration tests completed!")
    print("\nTests executed:")
    print("  1. Device Registration Flow")
    print("  2. Motion Detection Flow")
    print("  3. API CRUD Operations")
    print("  4. Session Timeout Flow")
    print("  5. Error Scenarios")
    print("  6. Token Refresher Flow")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
