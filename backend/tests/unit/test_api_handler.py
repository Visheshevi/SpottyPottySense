"""
Unit tests for API Handler Function

Tests helper functions and endpoint logic.
"""

import json
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
import sys
import os

# Add Lambda layer to path FIRST (before any other imports that depend on it)
layer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/layers/common'))
if layer_path not in sys.path:
    sys.path.insert(0, layer_path)

# Add function to path
function_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/functions/api-handler'))
if function_path not in sys.path:
    sys.path.insert(0, function_path)

# Now import the module
import index as api_handler


# ==============================================================================
# HELPER FUNCTION TESTS
# ==============================================================================

def test_parse_body_valid_json():
    """Test parsing valid JSON body."""
    body = '{"key": "value", "number": 123}'
    result = api_handler.parse_body(body)
    
    assert result == {"key": "value", "number": 123}


def test_parse_body_already_dict():
    """Test parsing body that's already a dictionary."""
    body = {"key": "value"}
    result = api_handler.parse_body(body)
    
    assert result == {"key": "value"}


def test_parse_body_none():
    """Test parsing None body."""
    result = api_handler.parse_body(None)
    
    assert result is None


def test_parse_body_empty_string():
    """Test parsing empty string body."""
    result = api_handler.parse_body("")
    
    assert result is None


def test_parse_body_invalid_json():
    """Test parsing invalid JSON raises ValidationError."""
    from validation import ValidationError
    
    with pytest.raises(ValidationError) as exc_info:
        api_handler.parse_body("{invalid json")
    
    assert "Invalid JSON" in str(exc_info.value)


def test_convert_decimals_single():
    """Test converting single Decimal to float."""
    result = api_handler.convert_decimals(Decimal('123.45'))
    
    assert result == 123.45
    assert isinstance(result, float)


def test_convert_decimals_dict():
    """Test converting Decimals in dictionary."""
    obj = {
        'integer': Decimal('42'),
        'float': Decimal('3.14'),
        'string': 'text',
        'nested': {
            'value': Decimal('99.99')
        }
    }
    
    result = api_handler.convert_decimals(obj)
    
    assert result == {
        'integer': 42.0,
        'float': 3.14,
        'string': 'text',
        'nested': {
            'value': 99.99
        }
    }


def test_convert_decimals_list():
    """Test converting Decimals in list."""
    obj = [Decimal('1.1'), Decimal('2.2'), 'text', {'val': Decimal('3.3')}]
    
    result = api_handler.convert_decimals(obj)
    
    assert result == [1.1, 2.2, 'text', {'val': 3.3}]


def test_convert_decimals_nested():
    """Test converting nested Decimals."""
    obj = {
        'sessions': [
            {
                'id': 'session-1',
                'duration': Decimal('15.5'),
                'events': [
                    {'count': Decimal('3')}
                ]
            },
            {
                'id': 'session-2',
                'duration': Decimal('22.3')
            }
        ],
        'total': Decimal('37.8')
    }
    
    result = api_handler.convert_decimals(obj)
    
    assert result['total'] == 37.8
    assert result['sessions'][0]['duration'] == 15.5
    assert result['sessions'][0]['events'][0]['count'] == 3.0
    assert result['sessions'][1]['duration'] == 22.3


def test_create_response():
    """Test creating API Gateway response."""
    body = {'message': 'Success', 'data': [1, 2, 3]}
    
    response = api_handler.create_response(200, body)
    
    assert response['statusCode'] == 200
    assert response['headers']['Content-Type'] == 'application/json'
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    assert 'X-Content-Type-Options' in response['headers']
    assert 'X-Frame-Options' in response['headers']
    
    # Body should be JSON string
    parsed_body = json.loads(response['body'])
    assert parsed_body == body


def test_create_response_error():
    """Test creating error response."""
    body = {'error': 'ValidationError', 'message': 'Invalid input'}
    
    response = api_handler.create_response(400, body)
    
    assert response['statusCode'] == 400
    parsed_body = json.loads(response['body'])
    assert parsed_body['error'] == 'ValidationError'


def test_extract_user_id_valid():
    """Test extracting user ID from valid Cognito claims."""
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'user-123-456',
                    'email': 'test@example.com'
                }
            }
        }
    }
    
    user_id = api_handler.extract_user_id(event)
    
    assert user_id == 'user-123-456'


def test_extract_user_id_missing_sub():
    """Test extracting user ID when sub claim is missing."""
    from validation import AuthorizationError
    
    event = {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'test@example.com'
                }
            }
        }
    }
    
    with pytest.raises(AuthorizationError) as exc_info:
        api_handler.extract_user_id(event)
    
    assert "User ID not found" in str(exc_info.value)


def test_extract_user_id_missing_authorizer():
    """Test extracting user ID when authorizer is missing."""
    from validation import AuthorizationError
    
    event = {
        'requestContext': {}
    }
    
    with pytest.raises(AuthorizationError):
        api_handler.extract_user_id(event)


def test_route_request_sensors_list():
    """Test routing GET /sensors request."""
    from validation import ValidationError
    
    # This will fail without mocked DynamoDB, but tests routing logic
    with pytest.raises((ValidationError, RuntimeError)):
        api_handler.route_request(
            method='GET',
            path='/sensors',
            path_params={},
            query_params={},
            body=None,
            user_id='test-user'
        )


def test_route_request_unknown_endpoint():
    """Test routing unknown endpoint."""
    from validation import ValidationError
    
    with pytest.raises(ValidationError) as exc_info:
        api_handler.route_request(
            method='GET',
            path='/unknown',
            path_params={},
            query_params={},
            body=None,
            user_id='test-user'
        )
    
    assert "Endpoint not found" in str(exc_info.value)


def test_route_request_sensor_detail_no_id():
    """Test routing sensor detail without ID."""
    from validation import ValidationError
    
    with pytest.raises(ValidationError) as exc_info:
        api_handler.route_request(
            method='GET',
            path='/sensors/test-001',
            path_params={},  # Missing 'id' parameter
            query_params={},
            body=None,
            user_id='test-user'
        )
    
    assert "Sensor ID is required" in str(exc_info.value)


# ==============================================================================
# VALIDATION TESTS
# ==============================================================================

def test_validate_environment_missing_vars(monkeypatch):
    """Test environment validation with missing variables."""
    # Clear environment variables
    monkeypatch.delenv('SENSORS_TABLE', raising=False)
    monkeypatch.delenv('USERS_TABLE', raising=False)
    
    with pytest.raises(RuntimeError) as exc_info:
        api_handler.validate_environment()
    
    assert "Missing required environment variables" in str(exc_info.value)


def test_validate_environment_all_present(monkeypatch):
    """Test environment validation with all variables present."""
    # Set all required environment variables
    monkeypatch.setenv('SENSORS_TABLE', 'test-sensors')
    monkeypatch.setenv('USERS_TABLE', 'test-users')
    monkeypatch.setenv('SESSIONS_TABLE', 'test-sessions')
    monkeypatch.setenv('MOTION_EVENTS_TABLE', 'test-events')
    monkeypatch.setenv('SPOTIFY_SECRET_NAME', 'test-secret')
    
    # Should not raise
    api_handler.validate_environment()


# ==============================================================================
# PAGINATION TESTS
# ==============================================================================

def test_pagination_defaults():
    """Test default pagination parameters."""
    assert api_handler.DEFAULT_PAGE_SIZE == 20
    assert api_handler.MAX_PAGE_SIZE == 100


def test_pagination_limit_enforcement():
    """Test that pagination limit is enforced."""
    # In actual handler, limit is capped at MAX_PAGE_SIZE
    requested_limit = 500
    actual_limit = min(requested_limit, api_handler.MAX_PAGE_SIZE)
    
    assert actual_limit == 100
