# 🎵 SpottyPottySense v2.0

> Automatically play Spotify when you enter a room - powered by AWS IoT and serverless architecture.

**Version 2.0** - Complete re-architecture from Raspberry Pi to AWS Serverless

[![AWS](https://img.shields.io/badge/AWS-IoT%20Core%20%7C%20Lambda%20%7C%20DynamoDB-orange)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Development](#development)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Cost Estimate](#cost-estimate)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

SpottyPottySense automatically detects when you enter a room (e.g., bathroom) and starts playing your favorite Spotify playlist. When you leave, it automatically stops playback after a configurable timeout.

**Use Cases:**
- 🚿 Bathroom music automation
- 🏃 Gym/workout room entry music
- 🍳 Kitchen cooking playlists
- 🛏️ Bedroom wake-up music

### What's New in v2.0?

| Feature | v1.0 (Old) | v2.0 (New) |
|---------|------------|------------|
| **Infrastructure** | Raspberry Pi (always-on) | AWS Serverless |
| **Scalability** | Single device | Unlimited devices |
| **Reliability** | 95% uptime | 99.9% uptime |
| **Cost** | ~$10/month | ~$2-5/month |
| **Management** | SSH + manual updates | Web dashboard |
| **Security** | Basic auth | Certificate-based + IAM |

---

## 🏗️ Architecture

```
┌─────────────┐
│  PIR Sensor │  Motion detected
└──────┬──────┘
       │
┌──────▼────────────┐
│  ESP32 Device     │  Publishes MQTT
│  (AWS IoT SDK)    │
└──────┬────────────┘
       │ MQTTS (TLS)
       │
┌──────▼────────────────────────┐
│      AWS IoT Core             │  Device management
└──────┬────────────────────────┘
       │ IoT Rules
       │
┌──────▼────────────────────────┐
│    AWS Lambda Functions       │  Business logic
│  - Motion Handler             │
│  - Token Refresher            │
│  - Timeout Checker            │
└──────┬────────────────────────┘
       │
   ┌───┴────┬─────────────┬──────────┐
   │        │             │          │
┌──▼──┐ ┌──▼──────┐ ┌────▼─────┐ ┌─▼─────┐
│ DDB │ │ Secrets │ │ CloudWatch│ │Spotify│
│State│ │ Manager │ │   Logs    │ │  API  │
└─────┘ └─────────┘ └───────────┘ └───────┘
```

**Key Components:**
- **AWS IoT Core**: Secure device connectivity via MQTT
- **AWS Lambda**: Serverless compute for event processing
- **Amazon DynamoDB**: State management and analytics
- **AWS Secrets Manager**: Secure credential storage
- **React Dashboard**: Web UI for management and analytics
- **ESP32 Device**: Motion sensor with AWS IoT SDK

For detailed architecture, see [TECHNICAL_SPECIFICATION.md](TECHNICAL_SPECIFICATION.md).

---

## ✨ Features

### Core Features
- ✅ **Automatic Playback**: Spotify starts when motion is detected
- ✅ **Auto-Stop**: Pauses after configurable timeout (default: 5 min)
- ✅ **Motion Debounce**: Prevents spam triggers (configurable gap)
- ✅ **Quiet Hours**: Disable during sleep hours (e.g., 10PM-7AM)
- ✅ **Multi-Room Support**: Configure multiple sensors/rooms
- ✅ **Device Management**: Select which Spotify device to play on

### Dashboard Features
- 📊 **Real-time Status**: See active sessions and sensor status
- 📈 **Analytics**: Usage patterns, session history, statistics
- ⚙️ **Configuration**: Update settings without code changes
- 🎵 **Playlist Management**: Select playlists per room
- 🔧 **Device Provisioning**: Add new sensors via web UI

### Enterprise Features
- 🔐 **Security**: Certificate-based authentication, encrypted secrets
- 📊 **Monitoring**: CloudWatch logs, metrics, and alarms
- 🔄 **High Availability**: Multi-AZ deployment, auto-recovery
- 💰 **Cost-Optimized**: Pay-per-use pricing (~$2-5/month)
- 🚀 **Scalable**: Supports unlimited devices and users

---

## 📦 Prerequisites

### Required Accounts
- ☑️ **AWS Account** ([Sign up](https://aws.amazon.com/))
  - IAM user with admin permissions
  - Credit card for billing (free tier eligible)
  
- ☑️ **Spotify Premium Account** ([Required](https://www.spotify.com/premium/))
  - Free tier doesn't support playback control
  
- ☑️ **Spotify Developer Account** ([Create app](https://developer.spotify.com/dashboard))
  - Get Client ID and Client Secret
  - Configure OAuth redirect URIs

### Required Software

| Tool | Version | Installation |
|------|---------|--------------|
| **Python** | 3.11+ | [python.org](https://www.python.org/) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) |
| **AWS CLI** | 2.15+ | [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| **AWS SAM CLI** | 1.107+ | [Install Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) |
| **Git** | 2.0+ | [git-scm.com](https://git-scm.com/) |

### Hardware (IoT Device)

**Option A: ESP32 DevKit** (Recommended - $8-12)
- ESP32-WROOM-32
- PIR Motion Sensor (HC-SR501)
- Breadboard, jumper wires
- Micro-USB cable

**Option B: Shelly Motion 2** (Easiest - $35)
- Pre-built, no coding required
- Battery or USB powered

**Option C: Aqara Motion Sensor** ($25 sensor + $60 hub)
- Zigbee-based, long battery life

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/SpottyPottySense.git
cd SpottyPottySense
```

### 2. Configure AWS

```bash
# Configure AWS credentials
aws configure

# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1
# - Default output format: json

# Verify
aws sts get-caller-identity
```

### 3. Set Up Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt
```

### 4. Configure Spotify

See [docs/SPOTIFY_SETUP.md](docs/SPOTIFY_SETUP.md) for detailed instructions:

1. Create Spotify Developer App
2. Get Client ID and Client Secret
3. Generate Refresh Token (use provided script)

### 5. Deploy Infrastructure

```bash
# Build SAM application
cd ..
sam build

# Deploy (interactive first time)
sam deploy --guided

# Answer prompts:
# Stack Name: spotty-potty-sense-dev
# AWS Region: us-east-1
# Environment: dev
# Confirm changes: Y
# Allow IAM role creation: Y
# Save config: Y
```

### 6. Store Secrets

```bash
# Run setup script (creates secrets in AWS)
./scripts/setup-secrets.sh dev

# Follow prompts to enter:
# - Spotify Client ID
# - Spotify Client Secret
# - Spotify Refresh Token
```

### 7. Create User

```bash
# Get User Pool ID from SAM outputs
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name spotty-potty-sense-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)

# Create Cognito user
aws cognito-idp admin-create-user \
  --user-pool-id ${USER_POOL_ID} \
  --username your.email@example.com \
  --user-attributes Name=email,Value=your.email@example.com Name=email_verified,Value=true \
  --temporary-password TempPass123!
```

### 8. Deploy Dashboard

```bash
cd dashboard

# Install dependencies
npm install

# Build
npm run build

# Deploy to S3 (use bucket name from SAM outputs)
aws s3 sync dist/ s3://your-dashboard-bucket-name/
```

### 9. Provision IoT Device

See [device-firmware/README.md](device-firmware/README.md) for device setup:

1. Flash firmware to ESP32
2. Provision device via dashboard
3. Upload certificates to device
4. Test motion detection

### 10. Test!

1. Open dashboard URL (from SAM outputs)
2. Login with Cognito credentials
3. View sensor status
4. Trigger motion sensor
5. Verify Spotify starts playing! 🎉

---

## 📁 Project Structure

```
SpottyPottySense/
├── backend/                    # Lambda functions and layers
│   ├── src/
│   │   ├── functions/         # Lambda function handlers
│   │   └── layers/            # Shared code (common utilities)
│   ├── tests/                 # Unit and integration tests
│   └── requirements.txt       # Python dependencies
│
├── dashboard/                  # React web dashboard
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── services/          # API client
│   │   └── stores/            # State management (Zustand)
│   └── package.json
│
├── device-firmware/            # ESP32 firmware (PlatformIO)
│   ├── src/
│   │   └── main.cpp          # Device code
│   └── platformio.ini
│
├── iot/                        # AWS IoT policies and rules
│   ├── policies/              # IoT device policies
│   └── rules/                 # IoT Rule Engine SQL
│
├── config/                     # Environment configurations
│   ├── dev/                   # Development config
│   ├── staging/               # Staging config
│   └── prod/                  # Production config
│
├── scripts/                    # Deployment and utility scripts
│   ├── deploy.sh              # Deploy backend
│   ├── setup-secrets.sh       # Initialize secrets
│   └── provision-device.sh    # Provision IoT device
│
├── legacy/                     # v1.0 code (archived)
│   └── v1.0/
│
├── template.yaml               # AWS SAM infrastructure definition
├── TECHNICAL_SPECIFICATION.md  # Detailed technical docs
└── README.md                   # This file
```

---

## 🛠️ Development

### Backend Development

```bash
cd backend
source .venv/bin/activate

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/
pylint src/

# Type check
mypy src/
```

### Frontend Development

```bash
cd dashboard

# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Lint
npm run lint
```

### Local Testing (SAM)

```bash
# Test Lambda function locally
sam local invoke MotionHandlerFunction -e events/motion-event.json

# Start local API
sam local start-api

# Start local Lambda endpoint
sam local start-lambda
```

---

## 🚢 Deployment

### Deploy to Development

```bash
./scripts/deploy.sh dev
```

### Deploy to Staging

```bash
./scripts/deploy.sh staging
```

### Deploy to Production

```bash
# Requires confirmation
./scripts/deploy.sh prod
```

### Manual Deployment

```bash
# Backend
sam build
sam deploy --config-env prod

# Dashboard
cd dashboard
npm run build
aws s3 sync dist/ s3://spotty-potty-dashboard-prod/
aws cloudfront create-invalidation --distribution-id E123 --paths "/*"
```

---

## ⚙️ Configuration

### Environment Variables

Create environment-specific config files in `config/`:

**config/dev/config.json:**
```json
{
  "environment": "dev",
  "region": "us-east-1",
  "logLevel": "DEBUG",
  "spotifyDefaultTimeout": 5,
  "motionDebounceMinutes": 2
}
```

### Sensor Configuration

Configure via dashboard or directly in DynamoDB `Sensors` table:

```json
{
  "sensorId": "bathroom_main",
  "location": "Main Bathroom",
  "spotifyDeviceId": "device_abc",
  "playlistUri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
  "preferences": {
    "timeoutMinutes": 5,
    "motionGapMinutes": 2,
    "quietHoursStart": "22:00",
    "quietHoursEnd": "07:00"
  }
}
```

---

## 🐛 Troubleshooting

### Common Issues

**1. Lambda functions not triggering**
- Check CloudWatch Logs for errors
- Verify IoT Rule is active
- Check device is publishing to correct topic

**2. Spotify not playing**
- Verify Spotify Premium account
- Check access token is valid (refresh if needed)
- Verify device is online in Spotify app
- Check Secrets Manager has correct credentials

**3. Device won't connect to AWS IoT**
- Verify certificates are uploaded correctly
- Check IoT Policy is attached to certificate
- Verify WiFi credentials
- Check IoT endpoint URL is correct

**4. Dashboard shows errors**
- Check API Gateway endpoint is correct
- Verify Cognito user pool configuration
- Check browser console for errors
- Verify CORS configuration

### Debugging

```bash
# View Lambda logs
sam logs -n MotionHandlerFunction --tail

# View CloudWatch logs
aws logs tail /aws/lambda/SpottyPottySense-MotionHandler-dev --follow

# Test IoT connectivity
aws iot-data publish \
  --topic sensors/test/motion \
  --payload '{"event":"motion_detected"}' \
  --cli-binary-format raw-in-base64-out

# Check DynamoDB items
aws dynamodb scan --table-name SpottyPottySense-Sensors-dev
```

---

## 💰 Cost Estimate

**Monthly cost for single user, 30 motion events/day:**

| Service | Cost |
|---------|------|
| IoT Core | $0.001 |
| Lambda | $0.006 |
| DynamoDB | $0.045 |
| Secrets Manager | $1.20 |
| API Gateway | $0.001 |
| CloudWatch | $0.25 |
| S3 + CloudFront | $0.087 |
| **Total** | **~$1.59/month** |

**Free tier covers most costs for first 12 months!**

Scales sub-linearly: 10 devices ≈ $5/month, 100 devices ≈ $25/month

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

- AWS for serverless infrastructure
- Spotify for the Web API
- PlatformIO for ESP32 development tools
- React community for excellent libraries

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/SpottyPottySense/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/SpottyPottySense/discussions)
- **Email**: your.email@example.com

---

**Made with ❤️ by [Your Name]**

*SpottyPottySense - Because every room deserves a soundtrack!* 🎵🚿
