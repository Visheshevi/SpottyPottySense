# SpottyPottySense Backend

AWS Lambda functions and shared layers for the SpottyPottySense v2.0 system.

## Directory Structure

```
backend/
├── src/
│   ├── functions/          # Lambda function handlers
│   │   ├── motion-handler/
│   │   ├── token-refresher/
│   │   ├── timeout-checker/
│   │   ├── session-manager/
│   │   ├── device-registration/
│   │   └── api-handler/
│   └── layers/             # Shared Lambda layers
│       └── common/
│           └── python/     # Shared Python modules
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
└── .venv/                 # Virtual environment (not in git)
```

## Setup

### 1. Create Virtual Environment

```bash
cd backend
python3 -m venv .venv
```

### 2. Activate Virtual Environment

**macOS/Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

### 3. Install Dependencies

**For development:**
```bash
pip install -r requirements-dev.txt
```

**For production only:**
```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -c "import boto3, requests, pydantic; print('Dependencies installed successfully!')"
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_motion_handler.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/
pylint src/

# Type checking
mypy src/
```

## Lambda Functions

Each Lambda function has its own directory under `src/functions/`:

- **motion-handler**: Processes motion detection events from IoT devices
- **token-refresher**: Refreshes Spotify OAuth tokens periodically
- **timeout-checker**: Checks for session timeouts and stops playback
- **session-manager**: Manages session lifecycle and analytics
- **device-registration**: Provisions new IoT devices
- **api-handler**: REST API backend for dashboard

## Shared Layers

The `common` layer contains shared utilities:

- **spotify_client.py**: Spotify API wrapper
- **dynamodb_helper.py**: DynamoDB operations
- **secrets_helper.py**: AWS Secrets Manager access
- **validation.py**: Pydantic models for validation
- **exceptions.py**: Custom exception classes
- **logger.py**: Structured logging

## Deployment

Functions are deployed via AWS SAM from the root directory:

```bash
cd ..
sam build
sam deploy
```

See root README.md for complete deployment instructions.

