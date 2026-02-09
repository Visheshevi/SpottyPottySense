# Integration Tests for SpottyPottySense

Comprehensive end-to-end testing suite for validating all backend components and workflows.

## Quick Start

### Prerequisites
```bash
# Install Python dependencies
pip install pytest boto3

# Configure AWS CLI
aws configure

# Verify stack is deployed
aws cloudformation describe-stacks --stack-name spotty-potty-sense --region us-east-2
```

### Run All Tests
```bash
# From project root
./scripts/run-integration-tests.sh

# Or with pytest directly
pytest backend/tests/integration/test_e2e_flow.py -v -s
```

### Run Specific Tests
```bash
# Run single test
pytest backend/tests/integration/test_e2e_flow.py::test_003_api_crud_operations -v -s

# Run with verbose output
./scripts/run-integration-tests.sh --verbose

# Run specific test pattern
pytest backend/tests/integration/ -k "api" -v
```

## Test Scenarios

### 1. Device Registration Flow (test_001)
**What it tests:**
- Sensor registration via Lambda
- DynamoDB record creation
- AWS IoT Thing provisioning
- Certificate generation and attachment

**Duration:** ~5 seconds

**Expected Result:** PASS
```
✓ Sensor registered successfully
✓ Sensor found in DynamoDB
✓ IoT Thing verified
✓ Certificate(s) attached
```

### 2. Motion Detection Flow (test_002)
**What it tests:**
- Motion event processing
- Session creation
- User/sensor setup
- Error handling

**Duration:** ~3 seconds

**Expected Result:** PASS (with Spotify API notes)

### 3. API CRUD Operations (test_003)
**What it tests:**
- GET /sensors - List sensors
- GET /sensors/{id} - Get sensor details
- PUT /sensors/{id} - Update sensor
- GET /users/me - Get user profile
- GET /analytics - Get statistics

**Duration:** ~3 seconds

**Expected Result:** PASS

### 4. Session Timeout Flow (test_004)
**What it tests:**
- Timeout detection
- Session completion
- Duration calculation
- Spotify pause logic

**Duration:** ~4 seconds

**Expected Result:** PASS

### 5. Error Scenarios (test_005)
**What it tests:**
- 404 Not Found (invalid sensor)
- 403 Forbidden (missing auth)
- 400 Bad Request (invalid data)

**Duration:** ~2 seconds

**Expected Result:** PASS

### 6. Token Refresher Flow (test_006)
**What it tests:**
- Token refresh Lambda
- Batch user processing
- Error handling

**Duration:** ~3 seconds

**Expected Result:** PASS

## Test Configuration

### Environment Variables
Tests automatically detect:
- AWS_REGION (default: us-east-2)
- STACK_NAME (default: spotty-potty-sense)
- Lambda function names from CloudFormation

### Fixtures
- `stack_outputs` - CloudFormation outputs
- `lambda_functions` - Function name mapping
- `test_user_id` - Test user identifier
- `test_sensor_id` - Unique sensor ID per test run
- `cleanup_sensor` - Automatic resource cleanup

### Resource Cleanup
Tests automatically clean up resources using the `cleanup_sensor` fixture:
- Sensors are deregistered after each test
- IoT Things and certificates are deleted
- DynamoDB records are removed

## Troubleshooting

### Test Fails: "Stack not found"
```bash
# Verify stack exists
aws cloudformation describe-stacks --stack-name spotty-potty-sense --region us-east-2

# If missing, deploy first
sam deploy --region us-east-2
```

### Test Fails: "Lambda function not found"
```bash
# Check function names
aws lambda list-functions --region us-east-2 | grep SpottyPottySense

# Rebuild and redeploy
sam build && sam deploy --region us-east-2
```

### Test Fails: "Permission denied"
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify IAM permissions for:
# - lambda:InvokeFunction
# - dynamodb:GetItem, PutItem, DeleteItem
# - iot:CreateThing, DescribeThing, DeleteThing
```

### Cleanup Orphaned Resources
```bash
# List orphaned sensors
aws dynamodb scan --table-name SpottyPottySense-Sensors-dev --region us-east-2

# List orphaned IoT Things
aws iot list-things --region us-east-2 | grep integration-test

# Manual cleanup (if needed)
aws lambda invoke \
  --function-name SpottyPottySense-DeviceRegistration-dev \
  --region us-east-2 \
  --payload '{"action":"deregister","sensorId":"SENSOR_ID"}' \
  response.json
```

## Performance Metrics

### Expected Response Times
| Operation | Cold Start | Warm Start |
|-----------|------------|------------|
| Lambda invocation | ~1000ms | ~10-50ms |
| API endpoint | ~1200ms | ~100-300ms |
| DynamoDB query | - | ~50-100ms |
| Full test suite | - | ~20 seconds |

### Success Criteria
- ✅ All tests pass
- ✅ Response time < 2s (P95)
- ✅ Error rate < 1%
- ✅ No resource leaks

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-2
      
      - name: Install Dependencies
        run: pip install -r backend/requirements-dev.txt
      
      - name: Run Integration Tests
        run: ./scripts/run-integration-tests.sh
```

## Related Documentation
- [PHASE_2.8_INTEGRATION_TESTING_COMPLETE.md](../../../PHASE_2.8_INTEGRATION_TESTING_COMPLETE.md) - Full test results
- [Load Testing Guide](../../../load-testing/README.md) - Performance testing
- [API Documentation](../../../PHASE_2.7_COMPLETE.md) - API endpoints

## Support
For issues or questions:
1. Check the troubleshooting section above
2. Review CloudWatch logs: `aws logs tail /aws/lambda/FUNCTION_NAME --follow`
3. Run tests with `--verbose` flag for detailed output
4. Check [PHASE_2.8_INTEGRATION_TESTING_COMPLETE.md](../../../PHASE_2.8_INTEGRATION_TESTING_COMPLETE.md) for known issues
