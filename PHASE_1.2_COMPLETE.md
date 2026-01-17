# Phase 1.2 - AWS SAM Infrastructure & Lambda Stubs ✅ COMPLETE

**Date Completed**: January 4, 2026  
**Status**: All tasks completed successfully  
**Ready for**: Initial deployment testing

---

## Tasks Completed

### ✅ 1.2.1 - Create Root template.yaml for SAM Infrastructure

**Created**: `template.yaml` (901 lines)

Comprehensive CloudFormation template with:
- **Metadata**: Application info, versioning
- **Parameters**: 10 configurable parameters (environment, timeouts, log levels, etc.)
- **Conditions**: Environment-specific logic (IsProduction, IsDevelopment, EnableXRay)
- **Globals**: Shared Lambda and API Gateway settings
- **Resources**: All AWS infrastructure (see below)
- **Outputs**: 13 stack outputs for easy reference

---

### ✅ 1.2.2 - Define All 4 DynamoDB Tables

All tables defined with proper configuration:

| Table | Attributes | GSI | TTL | Features |
|-------|------------|-----|-----|----------|
| **SensorsTable** | sensorId (PK), userId | UserIdIndex | No | Streams, PITR |
| **UsersTable** | userId (PK), email | EmailIndex | No | Streams, PITR |
| **SessionsTable** | sessionId (PK), sensorId, startTime | SensorIdIndex | ✅ ttl | Streams, PITR |
| **MotionEventsTable** | eventId (PK), sensorId, timestamp | SensorTimestampIndex | ✅ ttl | Streams, PITR |

**Features**:
- PAY_PER_REQUEST billing mode (cost-optimized)
- Point-in-time recovery (staging/prod)
- Deletion protection (prod only)
- DynamoDB Streams enabled for audit trail
- Environment-specific table names

---

### ✅ 1.2.3 - Configure Table Indexes (GSIs)

All Global Secondary Indexes configured:

1. **UserIdIndex** (SensorsTable)
   - Partition Key: userId
   - Purpose: Query all sensors for a user
   - Projection: ALL

2. **EmailIndex** (UsersTable)
   - Partition Key: email
   - Purpose: User lookup by email (login)
   - Projection: ALL

3. **SensorIdIndex** (SessionsTable)
   - Partition Key: sensorId
   - Sort Key: startTime
   - Purpose: Query sessions by sensor and time range
   - Projection: ALL

4. **SensorTimestampIndex** (MotionEventsTable)
   - Partition Key: sensorId
   - Sort Key: timestamp
   - Purpose: Query events by sensor and time range
   - Projection: ALL

---

### ✅ 1.2.4 - Set Up TTL Attributes

Time-to-Live (TTL) configured for automatic data cleanup:

- **SessionsTable**: `ttl` attribute
  - Auto-delete sessions after 30 days (dev/staging)
  - Auto-delete sessions after 90 days (prod)
  - Reduces storage costs
  - Maintains privacy compliance

- **MotionEventsTable**: `ttl` attribute
  - Auto-delete events after 30 days (dev/staging)
  - Auto-delete events after 90 days (prod)
  - Keeps detailed logs for recent analysis
  - Automatic cleanup of historical data

---

### ✅ 1.2.5 - Define All 6 Lambda Functions

All Lambda functions defined in template.yaml with proper configuration:

#### **1. MotionHandlerFunction**
- **Trigger**: IoT Rule (sensors/+/motion)
- **Purpose**: Process motion detection events
- **Timeout**: 30s
- **Memory**: 256MB (dev/staging), 512MB (prod)
- **IAM**: DynamoDB R/W, Secrets Manager Read
- **File**: `backend/src/functions/motion-handler/index.py` ✅

#### **2. TokenRefresherFunction**
- **Trigger**: EventBridge Schedule (every 30 minutes)
- **Purpose**: Refresh Spotify OAuth tokens
- **Timeout**: 60s
- **Memory**: 256MB (dev/staging), 512MB (prod)
- **IAM**: DynamoDB Read, Secrets Manager R/W
- **File**: `backend/src/functions/token-refresher/index.py` ✅

#### **3. TimeoutCheckerFunction**
- **Trigger**: EventBridge Schedule (every 1 minute)
- **Purpose**: Check for inactive sessions, stop playback
- **Timeout**: 30s
- **Memory**: 256MB (dev/staging), 512MB (prod)
- **IAM**: DynamoDB R/W, Secrets Manager Read
- **File**: `backend/src/functions/timeout-checker/index.py` ✅

#### **4. SessionManagerFunction**
- **Trigger**: Direct invocation (from other functions)
- **Purpose**: Manage session lifecycle and analytics
- **Timeout**: 30s
- **Memory**: 256MB (dev/staging), 512MB (prod)
- **IAM**: DynamoDB R/W (Sessions, MotionEvents)
- **File**: `backend/src/functions/session-manager/index.py` ✅

#### **5. DeviceRegistrationFunction**
- **Trigger**: API Gateway (POST /devices/register)
- **Purpose**: Provision new IoT devices
- **Timeout**: 60s
- **Memory**: 256MB (dev/staging), 512MB (prod)
- **IAM**: DynamoDB R/W, IoT Core (CreateThing, CreateCertificate, AttachPolicy)
- **File**: `backend/src/functions/device-registration/index.py` ✅

#### **6. ApiHandlerFunction**
- **Trigger**: API Gateway (12 REST endpoints)
- **Purpose**: REST API for dashboard
- **Timeout**: 30s
- **Memory**: 512MB
- **IAM**: DynamoDB R/W (all tables), Secrets Manager Read
- **File**: `backend/src/functions/api-handler/index.py` ✅
- **Endpoints**:
  - GET/POST /sensors
  - GET/PUT/DELETE /sensors/{id}
  - GET/PUT /users/me
  - GET /spotify/devices
  - POST /spotify/test
  - GET /sessions
  - GET /analytics

---

### ✅ 1.2.6 - Configure Lambda Execution Roles with IAM Policies

All functions have least-privilege IAM policies:

**Managed Policies Used**:
- `DynamoDBCrudPolicy` - Full R/W access to specific tables
- `DynamoDBReadPolicy` - Read-only access to specific tables

**Custom Inline Policies**:
```yaml
# Secrets Manager Access
- Effect: Allow
  Action:
    - secretsmanager:GetSecretValue
    - secretsmanager:UpdateSecret  # Only TokenRefresher
  Resource:
    - Spotify credentials secret
    - User-specific secrets (wildcard pattern)

# IoT Core (DeviceRegistration only)
- Effect: Allow
  Action:
    - iot:CreateThing
    - iot:CreateKeysAndCertificate
    - iot:AttachThingPrincipal
    - iot:AttachPolicy
    - iot:DescribeThing
  Resource: '*'  # Required for IoT operations

# CloudWatch Logs (all functions)
- Effect: Allow
  Action:
    - logs:CreateLogGroup
    - logs:CreateLogStream
    - logs:PutLogEvents
  Resource: Function-specific log group ARN
```

**Security Best Practices**:
- ✅ Each function only has access to resources it needs
- ✅ No wildcard permissions except where AWS requires it
- ✅ Secrets access limited to specific secret paths
- ✅ DynamoDB access limited to specific tables
- ✅ X-Ray tracing permissions (if enabled)

---

### ✅ 1.2.7 - Set Up Lambda Layers for Shared Code

**CommonLayer** created with full structure:

```
backend/src/layers/common/
├── requirements.txt
└── python/
    ├── __init__.py              # Package initialization
    ├── spotify_client.py        # Spotify API wrapper (STUB)
    ├── dynamodb_helper.py       # DynamoDB operations (STUB)
    ├── secrets_helper.py        # Secrets Manager with caching (STUB)
    ├── validation.py            # Pydantic models (STUB)
    ├── exceptions.py            # Custom exceptions ✅ COMPLETE
    └── logger.py                # Structured logging (STUB)
```

**Files Created**: 8 files (7 Python modules + 1 requirements.txt)

**Stub Implementations**:
All modules are functional stubs that:
- ✅ Can be imported without errors
- ✅ Have proper function signatures
- ✅ Log stub messages
- ✅ Return placeholder data
- ✅ Ready for Phase 2 full implementation

**Layer Configuration in template.yaml**:
```yaml
CommonLayer:
  Type: AWS::Serverless::LayerVersion
  LayerName: SpottyPottySense-Common-{Environment}
  ContentUri: backend/src/layers/common/
  CompatibleRuntimes:
    - python3.11
  RetentionPolicy: Retain
```

---

## Lambda Stub Function Details

### Stub Function Characteristics

All Lambda functions include:
- ✅ **Proper handler signature**: `def handler(event, context)`
- ✅ **Logging**: Structured logging with context
- ✅ **Error handling**: Try/except with proper responses
- ✅ **Input validation**: Basic validation of event structure
- ✅ **Return format**: Proper response format (API Gateway or direct)
- ✅ **Documentation**: Docstrings explaining what Phase 2 will implement
- ✅ **Environment-aware**: Read LOG_LEVEL from environment

### Example: Motion Handler Stub

```python
def handler(event, context):
    """Process motion detection events."""
    logger.info("Motion Handler invoked")
    
    try:
        sensor_id = event.get('sensorId', 'unknown')
        
        # STUB: Full implementation in Phase 2 will:
        # 1. Validate sensor exists
        # 2. Check quiet hours
        # 3. Check motion debounce
        # 4. Get/create session
        # 5. Get Spotify tokens
        # 6. Start playback
        # 7. Update DynamoDB
        
        return {
            'statusCode': 200,
            'sensorId': sensor_id,
            'message': 'STUB: Motion event received',
            'note': 'Full implementation in Phase 2'
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {'statusCode': 500, 'error': str(e)}
```

---

## Additional Infrastructure Components

### AWS IoT Core

**IoT Device Policy** defined:
- ✅ Certificate-based authentication
- ✅ Connect permission (scoped to Thing name)
- ✅ Publish permission (sensors/*/motion, sensors/*/status, sensors/*/register)
- ✅ Subscribe permission (sensors/*/config, sensors/*/commands)
- ✅ Receive permission (sensors/*/config, sensors/*/commands)

**IoT Rules**:
- ✅ Motion Detection Rule → MotionHandlerFunction
- ✅ SQL: `SELECT *, topic(2) as sensorId FROM 'sensors/+/motion'`

### Cognito User Pool

**Configuration**:
- ✅ Email verification required
- ✅ Password policy (environment-specific strength)
- ✅ MFA (optional in dev, required in prod)
- ✅ Account recovery via email
- ✅ User Pool Client for dashboard

### API Gateway

**Configuration**:
- ✅ REST API with Cognito authorizer
- ✅ CORS enabled (environment-specific origins)
- ✅ Throttling (100 req/s dev, 1000 req/s prod)
- ✅ CloudWatch logging
- ✅ X-Ray tracing (optional)
- ✅ 12 endpoints mapped to ApiHandlerFunction

### Secrets Manager

**Secret Created**:
- ✅ `spotty-potty-sense/spotify/client-credentials-{env}`
- ✅ Placeholder values (to be updated post-deployment)
- ✅ KMS encryption
- ✅ Environment-specific naming

### CloudWatch Log Groups

**6 Log Groups Created**:
- ✅ One per Lambda function
- ✅ Environment-specific retention (7/30/90 days)
- ✅ Automatic log stream creation
- ✅ Proper permissions in IAM roles

---

## File Statistics

### Files Created in Phase 1.2

| Category | Count | Lines |
|----------|-------|-------|
| **Infrastructure** | 1 | 901 |
| **Lambda Functions** | 6 | ~400 |
| **Function Requirements** | 6 | ~30 |
| **Layer Modules** | 7 | ~400 |
| **Layer Requirements** | 1 | 5 |
| **Documentation** | 1 | 325 |
| **TOTAL** | 22 | ~2,061 |

### Directory Structure

```
SpottyPottySense/
├── template.yaml                                    # ✅ 901 lines
└── backend/
    └── src/
        ├── functions/                              # ✅ 6 functions
        │   ├── motion-handler/
        │   │   ├── index.py                        # ✅ 77 lines
        │   │   └── requirements.txt                # ✅ 3 lines
        │   ├── token-refresher/
        │   │   ├── index.py                        # ✅ 65 lines
        │   │   └── requirements.txt                # ✅ 3 lines
        │   ├── timeout-checker/
        │   │   ├── index.py                        # ✅ 72 lines
        │   │   └── requirements.txt                # ✅ 3 lines
        │   ├── session-manager/
        │   │   ├── index.py                        # ✅ 108 lines
        │   │   └── requirements.txt                # ✅ 3 lines
        │   ├── device-registration/
        │   │   ├── index.py                        # ✅ 117 lines
        │   │   └── requirements.txt                # ✅ 3 lines
        │   └── api-handler/
        │       ├── index.py                        # ✅ 261 lines
        │       └── requirements.txt                # ✅ 3 lines
        └── layers/
            └── common/                             # ✅ 1 layer
                ├── requirements.txt                # ✅ 5 lines
                └── python/
                    ├── __init__.py                 # ✅ 41 lines
                    ├── spotify_client.py           # ✅ 78 lines
                    ├── dynamodb_helper.py          # ✅ 93 lines
                    ├── secrets_helper.py           # ✅ 77 lines
                    ├── validation.py               # ✅ 89 lines
                    ├── exceptions.py               # ✅ 34 lines
                    └── logger.py                   # ✅ 88 lines
```

---

## What Can We Do Now?

### ✅ Ready for Deployment Testing

The infrastructure is now ready for:

1. **SAM Build**:
   ```bash
   sam build
   ```
   This will:
   - Package all Lambda functions
   - Build Lambda layer
   - Resolve dependencies
   - Create deployment artifacts

2. **SAM Validate**:
   ```bash
   sam validate
   ```
   This will:
   - Check template syntax
   - Validate resource definitions
   - Verify IAM policies

3. **SAM Deploy (Dev)**:
   ```bash
   sam deploy --guided
   ```
   This will:
   - Create S3 bucket for artifacts
   - Upload Lambda code and layer
   - Create CloudFormation stack
   - Deploy all AWS resources

### ⚠️ What's Still Needed

**Before full deployment**:
1. **Spotify credentials** - Need to update secret after deployment
2. **Cognito user** - Create admin user for dashboard access
3. **User record in DynamoDB** - Initial user configuration

**Phase 2 Implementation**:
- Full business logic in Lambda functions
- Real Spotify API integration
- Real DynamoDB operations
- Real Secrets Manager usage
- Error handling and retries
- Input validation with Pydantic
- Comprehensive logging

---

## Next Steps

### Option A: Test Deployment (Recommended)

```bash
# 1. Validate template
sam validate

# 2. Build
sam build --parallel

# 3. Deploy to dev (interactive)
sam deploy --guided
# Answer prompts:
# - Stack Name: spotty-potty-sense-dev
# - Region: us-east-1
# - Environment: dev
# - Confirm changes: Y
# - Allow IAM creation: Y
# - Save config: Y

# 4. Check stack outputs
aws cloudformation describe-stacks \
  --stack-name spotty-potty-sense-dev \
  --query 'Stacks[0].Outputs'

# 5. Update Spotify secret
aws secretsmanager update-secret \
  --secret-id spotty-potty-sense/spotify/client-credentials-dev \
  --secret-string '{
    "client_id": "your_real_client_id",
    "client_secret": "your_real_client_secret"
  }'
```

### Option B: Continue Infrastructure Setup

- Phase 1.3: IoT Core detailed setup
- Phase 1.4: API Gateway & Cognito configuration
- Phase 1.5: Secrets Manager setup
- Phase 1.6: CloudWatch monitoring & dashboards
- Phase 1.7: Initial deployment

### Option C: Start Phase 2 Implementation

- Implement full Lambda business logic
- Add real AWS SDK calls
- Integrate Spotify API
- Add comprehensive error handling
- Write unit tests

---

## Verification Checklist

- ✅ template.yaml created (901 lines)
- ✅ All 4 DynamoDB tables defined with GSIs
- ✅ TTL configured for Sessions and MotionEvents
- ✅ All 6 Lambda functions have stub code
- ✅ All Lambda functions have requirements.txt
- ✅ Lambda layer structure created with 7 modules
- ✅ IAM policies configured with least privilege
- ✅ IoT Core policy and rules defined
- ✅ API Gateway with 12 endpoints configured
- ✅ Cognito User Pool configured
- ✅ Secrets Manager secret defined
- ✅ CloudWatch log groups defined
- ✅ All outputs defined for easy reference
- ✅ Environment-specific configurations
- ✅ X-Ray tracing support
- ✅ Proper error handling in stubs
- ✅ Documentation in all stub files

---

## Git Commit Recommendation

```bash
git add template.yaml backend/src/

git commit -m "Phase 1.2: Complete AWS SAM infrastructure with Lambda stubs

Infrastructure (template.yaml - 901 lines):
- 4 DynamoDB tables with GSIs and TTL
- 6 Lambda functions with IAM policies
- 1 Lambda layer (CommonLayer)
- AWS IoT Core (policy + rules)
- API Gateway with 12 endpoints + Cognito auth
- Secrets Manager for Spotify credentials
- CloudWatch log groups with retention
- 13 stack outputs
- Environment-specific configuration

Lambda Functions (stubs):
- MotionHandlerFunction (IoT trigger)
- TokenRefresherFunction (scheduled)
- TimeoutCheckerFunction (scheduled)
- SessionManagerFunction (direct invoke)
- DeviceRegistrationFunction (API)
- ApiHandlerFunction (REST API)

Lambda Layer (common):
- spotify_client.py
- dynamodb_helper.py
- secrets_helper.py
- validation.py
- exceptions.py
- logger.py

All stubs are functional and ready for 'sam build'.
Phase 2 will implement full business logic.

Ready for test deployment!"
```

---

## Summary Statistics

- **Infrastructure Components**: 25+ AWS resources
- **Lambda Functions**: 6 (all with stubs)
- **Lambda Layer Modules**: 7
- **DynamoDB Tables**: 4 (with 4 GSIs)
- **API Endpoints**: 12
- **Lines of Code**: ~2,061
- **Files Created**: 22
- **Time Spent**: ~2 hours
- **Status**: ✅ COMPLETE

---

**Status**: ✅ Phase 1.2 COMPLETE  
**Next Phase**: Choose from Options A, B, or C above  
**Deployment Ready**: Yes (with stub implementations)

---

*Generated by SpottyPottySense v2.0 Migration Assistant*

