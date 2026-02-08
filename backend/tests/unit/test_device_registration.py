import sys
import pytest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
FUNCTION_DIR = ROOT_DIR / "backend" / "src" / "functions" / "device-registration"
COMMON_LAYER_DIR = ROOT_DIR / "backend" / "src" / "layers" / "common"

sys.path.insert(0, str(FUNCTION_DIR))
sys.path.insert(0, str(COMMON_LAYER_DIR))

import index as device_registration
from exceptions import ValidationError


def test_parse_request_body_api_gateway():
    """Test parsing API Gateway request with body field."""
    event = {
        'body': '{"sensorId":"test-001","location":"Bathroom","userId":"user-123"}'
    }
    body = device_registration.parse_request_body(event)
    
    assert body['sensorId'] == 'test-001'
    assert body['location'] == 'Bathroom'
    assert body['userId'] == 'user-123'


def test_parse_request_body_direct():
    """Test parsing direct invocation without body field."""
    event = {
        'sensorId': 'test-001',
        'location': 'Bathroom',
        'userId': 'user-123'
    }
    body = device_registration.parse_request_body(event)
    
    assert body['sensorId'] == 'test-001'
    assert body['location'] == 'Bathroom'


def test_validate_input_valid():
    """Test validation with valid inputs."""
    # Should not raise exception
    device_registration.validate_input('bathroom-main', 'Main Bathroom', 'user-123')


def test_validate_input_missing_sensor_id():
    """Test validation fails when sensorId is missing."""
    with pytest.raises(ValidationError) as exc_info:
        device_registration.validate_input(None, 'Main Bathroom', 'user-123')
    
    assert 'sensorId is required' in str(exc_info.value)


def test_validate_input_missing_location():
    """Test validation fails when location is missing."""
    with pytest.raises(ValidationError) as exc_info:
        device_registration.validate_input('bathroom-main', None, 'user-123')
    
    assert 'location is required' in str(exc_info.value)


def test_validate_input_missing_user_id():
    """Test validation fails when userId is missing."""
    with pytest.raises(ValidationError) as exc_info:
        device_registration.validate_input('bathroom-main', 'Main Bathroom', None)
    
    assert 'userId is required' in str(exc_info.value)


def test_validate_input_invalid_characters():
    """Test validation fails with invalid characters in sensorId."""
    with pytest.raises(ValidationError) as exc_info:
        device_registration.validate_input('bathroom@main!', 'Bathroom', 'user-123')
    
    assert 'alphanumeric' in str(exc_info.value).lower()


def test_validate_input_too_short():
    """Test validation fails when sensorId is too short."""
    with pytest.raises(ValidationError) as exc_info:
        device_registration.validate_input('ab', 'Bathroom', 'user-123')
    
    assert 'between 3 and 128 characters' in str(exc_info.value)


def test_validate_input_too_long():
    """Test validation fails when sensorId is too long."""
    long_id = 'a' * 129
    with pytest.raises(ValidationError) as exc_info:
        device_registration.validate_input(long_id, 'Bathroom', 'user-123')
    
    assert 'between 3 and 128 characters' in str(exc_info.value)


def test_validate_input_valid_formats():
    """Test validation passes with various valid sensorId formats."""
    valid_ids = [
        'bathroom-main',
        'sensor_001',
        'bathroom-1-main',
        'sensor123',
        'BATHROOM_MAIN',
        'test-sensor-123_abc'
    ]
    
    for sensor_id in valid_ids:
        # Should not raise exception
        device_registration.validate_input(sensor_id, 'Location', 'user-123')


def test_format_response_api_gateway():
    """Test response formatting for API Gateway."""
    event = {'body': '{}'}
    body = {'message': 'Success', 'sensorId': 'test-001'}
    
    response = device_registration.format_response(event, 200, body)
    
    assert response['statusCode'] == 200
    assert 'headers' in response
    assert response['headers']['Content-Type'] == 'application/json'
    assert 'body' in response
    
    import json
    parsed_body = json.loads(response['body'])
    assert parsed_body['message'] == 'Success'


def test_format_response_direct():
    """Test response formatting for direct invocation."""
    event = {'sensorId': 'test-001'}
    body = {'message': 'Success', 'sensorId': 'test-001'}
    
    response = device_registration.format_response(event, 200, body)
    
    assert response['statusCode'] == 200
    assert response['message'] == 'Success'
    assert 'headers' not in response
    assert 'body' not in response


def test_extract_cert_id_from_arn():
    """Test extracting certificate ID from ARN."""
    cert_arn = "arn:aws:iot:us-east-2:123456789012:cert/abc123def456"
    cert_id = device_registration.extract_cert_id_from_arn(cert_arn)
    
    assert cert_id == "abc123def456"


def test_extract_cert_id_from_arn_no_slash():
    """Test extracting cert ID when ARN has no slash (just the ID)."""
    cert_id = device_registration.extract_cert_id_from_arn("abc123def456")
    
    assert cert_id == "abc123def456"
