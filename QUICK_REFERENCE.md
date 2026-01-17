# SpottyPottySense - Quick Reference Guide

**Last Updated:** 2026-01-17  
**Current Phase:** Phase 1 Complete ✅

---

## 🚀 Deployment Commands

### Build
```bash
sam build --region us-east-2
```

### Deploy
```bash
sam deploy --region us-east-2
```

### Deploy with Confirmation
```bash
sam deploy --region us-east-2 --no-confirm-changeset
```

### Validate Template
```bash
sam validate --region us-east-2
```

---

## 🔍 Monitoring Commands

### View Lambda Logs (Real-time)
```bash
# Motion Handler
sam logs -n MotionHandlerFunction --stack-name spotty-potty-sense --region us-east-2 --tail

# Token Refresher
sam logs -n TokenRefresherFunction --stack-name spotty-potty-sense --region us-east-2 --tail

# API Handler
sam logs -n ApiHandlerFunction --stack-name spotty-potty-sense --region us-east-2 --tail
```

### View API Gateway Access Logs
```bash
# Real-time tail
aws logs tail /aws/apigateway/SpottyPottySense-dev --region us-east-2 --follow

# Filter by errors (status >= 400)
aws logs filter-log-events \
  --log-group-name /aws/apigateway/SpottyPottySense-dev \
  --filter-pattern "{ $.status >= 400 }" \
  --region us-east-2
```

### Check Stack Status
```bash
aws cloudformation describe-stacks \
  --stack-name spotty-potty-sense \
  --region us-east-2 \
  --query 'Stacks[0].StackStatus'
```

### List All Stack Resources
```bash
aws cloudformation list-stack-resources \
  --stack-name spotty-potty-sense \
  --region us-east-2 \
  --output table
```

---

## 📊 Stack Outputs

### Get All Outputs
```bash
aws cloudformation describe-stacks \
  --stack-name spotty-potty-sense \
  --region us-east-2 \
  --query 'Stacks[0].Outputs' \
  --output table
```

### Key Outputs (Current)
```
API Gateway URL: https://ef389itm09.execute-api.us-east-2.amazonaws.com/dev
IoT Endpoint: 219250094707.iot.us-east-2.amazonaws.com
User Pool ID: us-east-2_kUrNN5nQ4
Client ID: 33cv0uu4ipt8e1sojut5e785kn
Access Logs: /aws/apigateway/SpottyPottySense-dev
```

---

## 🔐 Secrets Management

### Get Spotify Client Credentials
```bash
aws secretsmanager get-secret-value \
  --secret-id spotty-potty-sense/spotify/client-credentials-dev \
  --region us-east-2 \
  --query 'SecretString' \
  --output text | jq
```

### Update Spotify Client Credentials
```bash
aws secretsmanager put-secret-value \
  --secret-id spotty-potty-sense/spotify/client-credentials-dev \
  --region us-east-2 \
  --secret-string '{"clientId":"YOUR_CLIENT_ID","clientSecret":"YOUR_CLIENT_SECRET"}'
```

### List All Secrets
```bash
aws secretsmanager list-secrets \
  --region us-east-2 \
  --filters Key=name,Values=spotty-potty-sense \
  --query 'SecretList[*].[Name,ARN]' \
  --output table
```

---

## 🗄️ DynamoDB Operations

### Scan Sensors Table
```bash
aws dynamodb scan \
  --table-name SpottyPottySense-Sensors-dev \
  --region us-east-2 \
  --output table
```

### Get User by ID
```bash
aws dynamodb get-item \
  --table-name SpottyPottySense-Users-dev \
  --region us-east-2 \
  --key '{"userId":{"S":"USER_ID_HERE"}}'
```

### List All Tables
```bash
aws dynamodb list-tables \
  --region us-east-2 \
  --query 'TableNames[?contains(@, `SpottyPottySense`)]'
```

---

## 🔌 IoT Core Operations

### Publish Test Motion Event
```bash
aws iot-data publish \
  --topic sensors/test-sensor-001/motion \
  --region us-east-2 \
  --payload '{"sensorId":"test-sensor-001","event":"motion_detected","timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'
```

### List IoT Things
```bash
aws iot list-things \
  --region us-east-2 \
  --attribute-name thingTypeName \
  --attribute-value SpottyPottySensor
```

### Describe IoT Endpoint
```bash
aws iot describe-endpoint \
  --endpoint-type iot:Data-ATS \
  --region us-east-2
```

### List IoT Rules
```bash
aws iot list-topic-rules \
  --region us-east-2 \
  --query 'rules[?contains(ruleName, `SpottyPotty`)]' \
  --output table
```

---

## 👤 Cognito Operations

### Create Test User
```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-2_kUrNN5nQ4 \
  --region us-east-2 \
  --username test@example.com \
  --user-attributes Name=email,Value=test@example.com Name=name,Value="Test User" \
  --temporary-password "TempPass123!"
```

### List Users
```bash
aws cognito-idp list-users \
  --user-pool-id us-east-2_kUrNN5nQ4 \
  --region us-east-2 \
  --output table
```

### Get User
```bash
aws cognito-idp admin-get-user \
  --user-pool-id us-east-2_kUrNN5nQ4 \
  --region us-east-2 \
  --username test@example.com
```

---

## 🧪 Testing API Endpoints

### Health Check (No Auth)
```bash
curl https://ef389itm09.execute-api.us-east-2.amazonaws.com/dev/
```

### List Sensors (With Auth)
```bash
curl -X GET \
  https://ef389itm09.execute-api.us-east-2.amazonaws.com/dev/sensors \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Create Sensor (With Auth)
```bash
curl -X POST \
  https://ef389itm09.execute-api.us-east-2.amazonaws.com/dev/sensors \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sensorId": "sensor-001",
    "name": "Bathroom Sensor",
    "location": "Main Bathroom"
  }'
```

---

## 🗑️ Cleanup Commands

### Delete Stack (CAUTION!)
```bash
sam delete --stack-name spotty-potty-sense --region us-east-2
```

### Empty S3 Bucket Before Delete
```bash
aws s3 rm s3://aws-sam-cli-managed-default-samclisourcebucket-gorgpynnrkt3/spotty-potty-sense/ --recursive --region us-east-2
```

---

## 📁 Project Structure

```
SpottyPottySense/
├── backend/
│   ├── src/
│   │   ├── functions/              # Lambda functions (6)
│   │   │   ├── motion-handler/
│   │   │   ├── token-refresher/
│   │   │   ├── timeout-checker/
│   │   │   ├── session-manager/
│   │   │   ├── device-registration/
│   │   │   └── api-handler/
│   │   └── layers/                 # Common utilities
│   │       └── common/
│   │           └── python/
│   ├── requirements.txt            # Core dependencies
│   └── requirements-dev.txt        # Dev dependencies
├── iot/
│   ├── thing-types/                # IoT Thing Types
│   ├── policies/                   # IoT Policies
│   ├── rules/                      # IoT Rules SQL
│   ├── endpoints-config.json       # IoT Endpoints
│   └── MQTT_TOPICS.md              # Topic documentation
├── config/
│   ├── dev/                        # Dev environment
│   ├── staging/                    # Staging environment
│   └── prod/                       # Prod environment
├── scripts/                        # Deployment scripts
├── docs/                           # Documentation
├── template.yaml                   # SAM template (882 lines)
├── samconfig.toml                  # SAM configuration
└── README.md                       # Project README
```

---

## 🔧 Environment Variables

### SAM Template Parameters (Current Dev)
```
Environment: dev
LogLevel: INFO
SpotifyDefaultTimeoutMinutes: 5
MotionDebounceMinutes: 2
TokenRefreshIntervalMinutes: 30
TimeoutCheckIntervalMinutes: 2
SessionTTLDays: 30
EnableXRayTracing: true
AlarmEmail: (not set)
```

### Update Parameter
```bash
# Edit samconfig.toml and redeploy
sam deploy --region us-east-2
```

---

## 📚 Documentation Files

1. `README.md` - Project overview
2. `TECHNICAL_SPECIFICATION.md` - Architecture spec
3. `PHASE_1_COMPLETE.md` - Phase 1 summary
4. `PHASE_1.1_COMPLETE.md` - Project structure
5. `PHASE_1.2_COMPLETE.md` - SAM template
6. `PHASE_1.3_COMPLETE.md` - IoT Core
7. `PHASE_1.4_COMPLETE.md` - API Gateway
8. `PHASE_1.4_VERIFICATION.md` - API verification
9. `iot/MQTT_TOPICS.md` - MQTT documentation
10. `QUICK_REFERENCE.md` - This file

---

## 🎯 Next Steps

**Current Status:** Phase 1 Complete ✅  
**Next Phase:** Phase 2.1 - Common Layer Implementation

**To Start Phase 2.1:**
1. Read `TECHNICAL_SPECIFICATION.md` Section 5.2.1
2. Implement Spotify API client
3. Implement DynamoDB helpers
4. Set up data validation
5. Configure structured logging

---

## 🆘 Troubleshooting

### Lambda Function Not Invoking
```bash
# Check CloudWatch Logs
sam logs -n FunctionName --stack-name spotty-potty-sense --region us-east-2

# Check Lambda function exists
aws lambda get-function --function-name SpottyPottySense-MotionHandler-dev --region us-east-2
```

### API Gateway 403 Errors
- Check Cognito token is valid
- Verify Authorization header format: `Bearer <token>`
- Check Cognito user pool client ID matches

### DynamoDB Access Errors
- Verify IAM role has correct permissions
- Check table name matches environment (e.g., `SpottyPottySense-Sensors-dev`)

### IoT Connection Issues
- Verify IoT endpoint is correct
- Check device certificate is valid
- Verify IoT policy allows required actions

---

## 📞 Useful AWS Console Links

- **CloudFormation:** https://console.aws.amazon.com/cloudformation
- **Lambda:** https://console.aws.amazon.com/lambda
- **API Gateway:** https://console.aws.amazon.com/apigateway
- **DynamoDB:** https://console.aws.amazon.com/dynamodb
- **IoT Core:** https://console.aws.amazon.com/iot
- **Cognito:** https://console.aws.amazon.com/cognito
- **CloudWatch:** https://console.aws.amazon.com/cloudwatch
- **Secrets Manager:** https://console.aws.amazon.com/secretsmanager

---

*Quick Reference Version 1.0 - 2026-01-17*

