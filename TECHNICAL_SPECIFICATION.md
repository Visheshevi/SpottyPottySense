# SpottyPottySense - Technical Specification & Implementation Guide

**Version**: 2.0  
**Date**: January 2026  
**Author**: Architecture Team  
**Status**: Design Complete - Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Background & Motivation](#background--motivation)
3. [Original Architecture (v1.0)](#original-architecture-v10)
4. [Problems with Original Design](#problems-with-original-design)
5. [New Architecture (v2.0)](#new-architecture-v20)
6. [Technology Stack](#technology-stack)
7. [Detailed Component Design](#detailed-component-design)
8. [Data Models](#data-models)
9. [API Specifications](#api-specifications)
10. [Security Architecture](#security-architecture)
11. [Implementation Plan](#implementation-plan)
12. [Testing Strategy](#testing-strategy)
13. [Deployment Guide](#deployment-guide)
14. [Cost Analysis](#cost-analysis)
15. [Future Enhancements](#future-enhancements)

---

## Executive Summary

**SpottyPottySense** is an IoT motion detection system that automatically plays Spotify music when someone enters a room (e.g., bathroom). The original implementation used a Raspberry Pi server and ESP8266 microcontroller. This document outlines the complete re-architecture to a serverless AWS-based solution.

### Key Improvements in v2.0

| Aspect | v1.0 (Old) | v2.0 (New) |
|--------|------------|------------|
| **Infrastructure** | Raspberry Pi (always-on) | AWS Serverless (pay-per-use) |
| **Scalability** | Single device | Unlimited devices |
| **Reliability** | Single point of failure | Multi-AZ, auto-recovery |
| **Cost** | ~$5/month + hardware | ~$2-5/month, no hardware |
| **Maintenance** | Manual OS updates, patches | Fully managed by AWS |
| **Security** | Local WiFi, basic auth | Certificate-based, encrypted |
| **Monitoring** | Basic logs | CloudWatch, X-Ray, dashboards |
| **Multi-user** | Single user only | Multi-user support |

### Project Objectives

1. ✅ Replace Raspberry Pi with AWS serverless infrastructure
2. ✅ Upgrade ESP8266 to AWS IoT compatible device (ESP32 or Shelly Motion 2)
3. ✅ Implement enterprise-grade security and monitoring
4. ✅ Support multiple rooms and users
5. ✅ Build web dashboard for management and analytics
6. ✅ Reduce operational costs and complexity
7. ✅ Enable easy scaling and future enhancements

---

## Background & Motivation

### The Problem

Many people enjoy listening to music during daily routines (showering, getting ready, etc.) but find it inconvenient to manually:
- Pull out their phone
- Unlock it
- Open Spotify
- Start playback
- Select the right device/speaker

**Solution**: Automatically detect when someone enters the room and start Spotify playback immediately.

### Use Cases

1. **Primary**: Bathroom music - automatically play when entering bathroom
2. **Secondary**: Bedroom wake-up music
3. **Tertiary**: Kitchen cooking music
4. **Future**: Multi-room coordination, smart home integration

### Target Users

- Tech-savvy homeowners
- Spotify Premium subscribers
- Smart home enthusiasts
- Developers interested in IoT projects

---

## Original Architecture (v1.0)

### Component Overview

```
┌─────────────────┐
│  PIR Sensor     │
│  (Motion)       │
└────────┬────────┘
         │
         │ GPIO
         ▼
┌─────────────────┐
│  ESP8266        │
│  (NodeMCU v2)   │
│  - WiFi         │
│  - MQTT Client  │
└────────┬────────┘
         │
         │ WiFi → MQTT (localhost:1883)
         ▼
┌─────────────────────────────┐
│  Raspberry Pi               │
│  ┌─────────────────────┐   │
│  │ Mosquitto MQTT      │   │
│  │ Broker              │   │
│  └──────────┬──────────┘   │
│             │               │
│  ┌──────────▼──────────┐   │
│  │ Python MQTT         │   │
│  │ Listener Service    │   │
│  └──────────┬──────────┘   │
│             │               │
│  ┌──────────▼──────────┐   │
│  │ Spotify API         │   │
│  │ Controller          │   │
│  └─────────────────────┘   │
└─────────────┬───────────────┘
              │
              │ HTTPS
              ▼
       ┌──────────────┐
       │ Spotify API  │
       │ (Cloud)      │
       └──────────────┘
```

### Hardware Components

1. **ESP8266 (NodeMCU v2)**
   - Microcontroller with WiFi
   - Connected to PIR motion sensor (GPIO 4)
   - LED indicator (GPIO 14)
   - Firmware: Arduino/PlatformIO

2. **PIR Motion Sensor (HC-SR501)**
   - Passive Infrared sensor
   - Detects motion up to 7 meters
   - 3.3V operation

3. **Raspberry Pi**
   - Model: Any (3B+, 4, Zero W)
   - OS: Raspbian
   - Always-on server
   - Power: 5V/2.5A

4. **Network**
   - Home WiFi (2.4GHz)
   - Internet connection required

### Software Components

#### ESP8266 Firmware (C++/Arduino)
```cpp
// Key files:
- main.cpp           // Main loop, motion detection
- constants.h        // Configuration (WiFi, MQTT)
- mqttConnect.cpp    // MQTT client logic
- wifiConnect.cpp    // WiFi connection logic
```

**Functionality**:
- Connect to WiFi
- Connect to local MQTT broker
- Detect motion via interrupt
- Publish motion events to topic: `motion.in.bathroom`
- Debounce: 2-minute gap between detections

#### Raspberry Pi Services (Python)

**1. Mosquitto MQTT Broker**
```bash
# Configuration: /etc/mosquitto/mosquitto.conf
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
```

**2. MQTT Listener (`mqtt_listener.py`)**
```python
# Key functionality:
- Subscribe to "motion.in.bathroom"
- On "motion detected": call spotify_start_on_device()
- On "no motion": call spotify_stop_on_device()
```

**3. Spotify Controller (`spotify_start_on_device.py`)**
```python
# Key functionality:
- refresh_access_token()    # Get new Spotify token
- request_device_to_play()  # Start playback
- request_device_to_stop()  # Pause playback
- Hardcoded: client_id, client_secret, refresh_token, device_id
```

### Data Flow (Original)

1. **Motion Detected**:
   ```
   PIR Sensor → ESP8266 (interrupt) 
   → WiFi → MQTT Broker (Raspberry Pi)
   → Python Listener → Spotify API Client
   → Spotify Web API → Speaker Starts Playing
   ```

2. **Timeout (No Motion)**:
   ```
   ESP8266 (timer: 5 min) → MQTT Publish "no motion"
   → Python Listener → Spotify API → Pause Playback
   ```

### Configuration

All configuration was **hardcoded** in source files:

```cpp
// ESP8266 constants.h
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "192.168.1.100";  // Raspberry Pi IP
const char* mqtt_user = "mqtt_user";
const char* mqtt_pass = "mqtt_password";
```

```python
# Python spotify_start_on_device.py
spotify_token = "hardcoded_token_here"
spotify_device_id = "hardcoded_device_id"
client_id = "hardcoded_client_id"
client_secret = "hardcoded_client_secret"
refresh_token = "hardcoded_refresh_token"
```

---

## Problems with Original Design

### 1. **Reliability Issues**
- ❌ Single point of failure: If Raspberry Pi crashes, entire system fails
- ❌ No automatic recovery or restart mechanisms
- ❌ Network issues require manual intervention
- ❌ Power outages require manual restart

### 2. **Scalability Limitations**
- ❌ Only supports one sensor (bathroom)
- ❌ Only supports one user/Spotify account
- ❌ Adding new rooms requires code changes
- ❌ Can't handle multiple simultaneous users

### 3. **Security Concerns**
- ❌ Credentials hardcoded in source code
- ❌ Credentials visible in Git history (if committed)
- ❌ MQTT credentials in plain text
- ❌ No encryption for local MQTT traffic
- ❌ Spotify tokens never rotated

### 4. **Maintenance Burden**
- ❌ Raspberry Pi OS requires regular updates
- ❌ Python dependencies need management
- ❌ Mosquitto MQTT broker needs configuration
- ❌ Manual service restart after crashes
- ❌ No centralized logging or monitoring
- ❌ Debugging requires SSH access to Pi

### 5. **Cost & Infrastructure**
- ❌ Raspberry Pi must run 24/7 (~$5/month electricity)
- ❌ Requires home network and port forwarding for remote access
- ❌ Hardware failure = downtime and replacement cost
- ❌ Static IP or dynamic DNS needed

### 6. **User Experience**
- ❌ No web interface for configuration
- ❌ No analytics or usage statistics
- ❌ No way to see current status remotely
- ❌ Configuration changes require code editing

### 7. **Development Workflow**
- ❌ Testing requires physical hardware
- ❌ Deployment requires manual SCP/SSH
- ❌ No CI/CD pipeline
- ❌ No automated testing

### 8. **Code Quality**
- ❌ Poor error handling (basic try-catch)
- ❌ No retry logic for API failures
- ❌ Inconsistent logging
- ❌ Mixed concerns (business logic + infrastructure)
- ❌ No input validation

---

## New Architecture (v2.0)

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User/Client Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Browser    │  │  Mobile App  │  │  IoT Device  │          │
│  │  (Dashboard) │  │   (Future)   │  │  (Sensor)    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          │ HTTPS            │ HTTPS            │ MQTTS (8883)
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────────┐
│                        AWS Cloud Layer                            │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │  CloudFront      │  │  API Gateway     │  │  IoT Core     │ │
│  │  (CDN)           │  │  (REST API)      │  │  (MQTT)       │ │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘ │
│           │                     │                     │          │
│           │                     │                     │          │
│  ┌────────▼─────────┐  ┌────────▼─────────┐  ┌───────▼───────┐ │
│  │   S3 Bucket      │  │   Cognito        │  │  IoT Rules    │ │
│  │   (Dashboard)    │  │   (Auth)         │  │  Engine       │ │
│  └──────────────────┘  └──────────────────┘  └───────┬───────┘ │
│                                                       │          │
│  ┌────────────────────────────────────────────────────▼───────┐ │
│  │                  AWS Lambda Functions                      │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │ │
│  │  │   Motion     │ │    Token     │ │   Timeout    │      │ │
│  │  │   Handler    │ │  Refresher   │ │   Checker    │      │ │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘      │ │
│  │  ┌──────▼───────┐ ┌──────▼───────┐ ┌──────▼───────┐      │ │
│  │  │   Session    │ │   Device     │ │     API      │      │ │
│  │  │   Manager    │ │ Registration │ │   Handler    │      │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘      │ │
│  └────────────────────────┬───────────────────────────────────┘ │
│                           │                                      │
│  ┌────────────────────────┼───────────────────────────────────┐ │
│  │         Data Layer     │                                   │ │
│  │  ┌──────────┐ ┌────────▼──────┐ ┌──────────────────────┐ │ │
│  │  │ Secrets  │ │   DynamoDB    │ │    CloudWatch        │ │ │
│  │  │ Manager  │ │   (4 Tables)  │ │    (Logs/Metrics)    │ │ │
│  │  └──────────┘ └───────────────┘ └──────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘│
└───────────────────────────────────┬───────────────────────────────┘
                                    │
                                    │ HTTPS
                                    ▼
                            ┌───────────────┐
                            │  Spotify API  │
                            │   (External)  │
                            └───────────────┘
```

### Architecture Principles

1. **Serverless-First**: No servers to manage, pay only for use
2. **Event-Driven**: React to IoT messages, timers, API calls
3. **Managed Services**: Use AWS managed services for reliability
4. **Security by Design**: Encryption, least privilege, secrets management
5. **Observable**: Comprehensive logging, metrics, and tracing
6. **Scalable**: Auto-scales from 1 to millions of devices
7. **Cost-Optimized**: Pay-per-request pricing, free tier friendly
8. **Multi-Tenant**: Support multiple users and devices

---

## Technology Stack

### Cloud Platform: **Amazon Web Services (AWS)**

#### Core Services

| Service | Purpose | Pricing Model |
|---------|---------|---------------|
| **AWS IoT Core** | Device connectivity, MQTT broker | $1.00 per million messages |
| **AWS Lambda** | Serverless compute for business logic | $0.20 per million requests |
| **Amazon DynamoDB** | NoSQL database for state | Pay per request (free tier: 25GB) |
| **AWS Secrets Manager** | Secure credential storage | $0.40 per secret per month |
| **Amazon API Gateway** | REST API for dashboard | $1.00 per million requests |
| **Amazon Cognito** | User authentication | Free tier: 50,000 MAU |
| **Amazon S3** | Dashboard static hosting | $0.023 per GB (free tier: 5GB) |
| **Amazon CloudFront** | CDN for dashboard | $0.085 per GB (free tier: 1TB) |
| **Amazon CloudWatch** | Logging, metrics, monitoring | $0.50 per GB logs |
| **Amazon EventBridge** | Scheduled events, event bus | $1.00 per million events |
| **AWS X-Ray** | Distributed tracing | $5.00 per million traces |

#### Development Tools

| Tool | Purpose | Version |
|------|---------|---------|
| **AWS SAM CLI** | Infrastructure as Code, local testing | 1.107.0+ |
| **AWS CLI** | AWS resource management | 2.15.0+ |
| **Python** | Lambda runtime | 3.11 |
| **Node.js** | Dashboard frontend | 18+ |

### IoT Device Options

#### Option A: ESP32 (Recommended)
- **Chip**: ESP32-WROOM-32
- **Features**: Dual-core, WiFi, Bluetooth, 520KB RAM
- **Cost**: $8-12
- **Development**: Arduino IDE or PlatformIO
- **AWS Support**: Native via AWS IoT Device SDK
- **Security**: Hardware acceleration for TLS 1.2

#### Option B: Shelly Motion 2 (Easiest)
- **Type**: Pre-built motion sensor
- **Features**: WiFi, MQTT, battery or USB powered
- **Cost**: $35
- **Configuration**: Web interface, no coding required
- **AWS Support**: Configure MQTT to point to AWS IoT endpoint

#### Option C: Aqara Motion Sensor + Hub
- **Sensor**: Aqara Motion Sensor P2
- **Hub**: Aqara Hub M2
- **Features**: Zigbee, long battery life
- **Cost**: $25 sensor + $60 hub
- **AWS Support**: Hub bridges Zigbee to WiFi/MQTT

### Backend Stack

#### Lambda Runtime: Python 3.11
- **Reason**: Best AWS SDK support, Spotify API libraries
- **Dependencies**:
  - `boto3` - AWS SDK
  - `requests` - HTTP client
  - `pydantic` - Data validation
  - `aws-lambda-powertools` - Observability

#### Lambda Layer: Shared Utilities
- **spotify_client.py** - Spotify API wrapper
- **dynamodb_helper.py** - Database operations
- **secrets_helper.py** - Secrets Manager access
- **validation.py** - Input validation
- **exceptions.py** - Custom exceptions
- **logger.py** - Structured logging

### Frontend Stack

#### Dashboard: React 18 + TypeScript
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite or Create React App
- **UI Library**: Tailwind CSS + Headless UI
- **State Management**: Zustand or React Context
- **API Client**: AWS Amplify or Axios
- **Authentication**: AWS Amplify Auth (Cognito)
- **Charts**: Recharts or Chart.js
- **Icons**: Heroicons or Lucide React

#### Dashboard Features
1. Real-time sensor status
2. Session history and analytics
3. Sensor configuration (CRUD)
4. Spotify device management
5. User preferences
6. Manual playback control
7. Usage statistics with graphs

### Infrastructure as Code: AWS SAM

#### SAM Template (`template.yaml`)
- Defines all AWS resources declaratively
- Version controlled in Git
- Multi-environment support (dev/staging/prod)
- Automated deployments via CLI

#### Alternative: Terraform (not chosen)
- More verbose
- Multi-cloud (not needed here)
- Steeper learning curve

### Version Control: Git + GitHub

#### Repository Structure
```
SpottyPottySense/
├── backend/              # Lambda functions
├── dashboard/            # React frontend
├── device-firmware/      # IoT device code
├── iot/                  # IoT policies and rules
├── config/               # Environment configs
├── scripts/              # Deployment scripts
└── template.yaml         # SAM template
```

### CI/CD: GitHub Actions (Future)

```yaml
# Automated pipeline:
on: push to main
→ Run tests
→ Build Lambda functions
→ Deploy to staging
→ Run integration tests
→ Manual approval
→ Deploy to production
```

---

## Detailed Component Design

### 1. AWS IoT Core

#### Purpose
- MQTT broker for device connectivity
- Message routing to Lambda functions
- Device authentication via X.509 certificates
- Device shadows for state management

#### MQTT Topics

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `sensors/{sensorId}/motion` | Device → AWS | Motion detected event |
| `sensors/{sensorId}/status` | Device → AWS | Device health/status |
| `sensors/{sensorId}/register` | Device → AWS | Device registration |
| `sensors/{sensorId}/config` | AWS → Device | Configuration updates |
| `sensors/{sensorId}/commands` | AWS → Device | Control commands |

#### Message Format

```json
// Motion Event
{
  "event": "motion_detected",
  "sensorId": "bathroom_main",
  "timestamp": 1704412800,
  "metadata": {
    "batteryLevel": 85,
    "signalStrength": -45
  }
}
```

#### IoT Rules

**Rule 1: Motion Detection**
```sql
SELECT *, topic(2) as sensorId 
FROM 'sensors/+/motion'
```
Action: Invoke `MotionHandlerFunction`

**Rule 2: Device Registration**
```sql
SELECT * 
FROM 'sensors/+/register'
```
Action: Invoke `DeviceRegistrationFunction`

#### Security

- **Authentication**: X.509 certificates (unique per device)
- **Authorization**: IoT Policy attached to certificate
- **Encryption**: TLS 1.2 for all connections
- **Policy**: Least privilege (publish/subscribe only to own topics)

#### Device Policy Template

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iot:Connect"],
      "Resource": ["arn:aws:iot:REGION:ACCOUNT:client/${iot:Connection.Thing.ThingName}"]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Publish"],
      "Resource": ["arn:aws:iot:REGION:ACCOUNT:topic/sensors/*/motion"]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Subscribe"],
      "Resource": ["arn:aws:iot:REGION:ACCOUNT:topicfilter/sensors/*/config"]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Receive"],
      "Resource": ["arn:aws:iot:REGION:ACCOUNT:topic/sensors/*/config"]
    }
  ]
}
```

### 2. AWS Lambda Functions

#### Function 1: Motion Handler

**Trigger**: IoT Core Rule (motion events)  
**Runtime**: Python 3.11  
**Timeout**: 30 seconds  
**Memory**: 256 MB

**Purpose**: Core business logic - process motion and start Spotify

**Input**:
```json
{
  "sensorId": "bathroom_main",
  "event": "motion_detected",
  "timestamp": 1704412800
}
```

**Logic Flow**:
```python
1. Validate input
2. Get sensor config from DynamoDB
3. Get user config from DynamoDB
4. Check quiet hours (e.g., 10PM - 7AM)
5. Check motion debounce (last motion < 2 min ago?)
6. Get Spotify access token from Secrets Manager
7. Check if already playing
8. Get or create active session
9. Call Spotify API to start playback
10. Update sensor lastMotionTime in DynamoDB
11. Update session with new motion event
12. Schedule timeout check (EventBridge)
13. Log success/failure
```

**Output**:
```json
{
  "statusCode": 200,
  "sessionId": "uuid",
  "action": "started_playback",
  "spotifyDevice": "bathroom_speaker"
}
```

**Error Handling**:
- Spotify API failure → Retry 3 times with exponential backoff
- Token expired → Trigger token refresh, retry
- Device offline → Log error, send SNS notification
- All errors logged to CloudWatch with context

**IAM Permissions**:
- DynamoDB: Read Sensors, Users; Write Sessions, MotionEvents
- Secrets Manager: Read Spotify tokens
- EventBridge: Put events
- CloudWatch: Write logs

#### Function 2: Token Refresher

**Trigger**: EventBridge (every 30 minutes)  
**Runtime**: Python 3.11  
**Timeout**: 60 seconds  
**Memory**: 256 MB

**Purpose**: Proactively refresh Spotify OAuth tokens

**Logic Flow**:
```python
1. Query all users from DynamoDB
2. For each user:
   a. Get refresh_token from Secrets Manager
   b. Call Spotify token refresh endpoint
   c. Get new access_token
   d. Update access_token in Secrets Manager
   e. Log success/failure
3. If failures > threshold, send SNS alert
```

**Spotify Token Refresh API**:
```python
POST https://accounts.spotify.com/api/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=REFRESH_TOKEN
&client_id=CLIENT_ID
&client_secret=CLIENT_SECRET
```

**Error Handling**:
- Refresh token invalid → Notify user (email/SNS)
- Network failure → Retry, log
- Rate limit → Exponential backoff

#### Function 3: Timeout Checker

**Trigger**: EventBridge (every 1 minute)  
**Runtime**: Python 3.11  
**Timeout**: 30 seconds  
**Memory**: 256 MB

**Purpose**: Stop Spotify after inactivity timeout

**Logic Flow**:
```python
1. Query active sessions from DynamoDB (endTime = null)
2. For each active session:
   a. Get sensor config (timeoutMinutes)
   b. Calculate time since lastMotionTime
   c. If elapsed > timeout:
      - Get Spotify token
      - Call Spotify API to pause playback
      - Update session endTime
      - Calculate session statistics
      - Update analytics
3. Clean up old completed sessions (TTL)
```

**DynamoDB Query**:
```python
# GSI: SessionStatusIndex
# Query: status = 'active'
# Filter: lastMotionTime < (now - timeout)
```

#### Function 4: Session Manager

**Trigger**: Direct invocation from other functions  
**Runtime**: Python 3.11  
**Timeout**: 30 seconds  
**Memory**: 256 MB

**Purpose**: Manage session lifecycle and analytics

**Operations**:

**A. Create Session**
```python
def create_session(sensor_id, user_id):
    session = {
        'sessionId': generate_uuid(),
        'sensorId': sensor_id,
        'userId': user_id,
        'startTime': current_timestamp(),
        'endTime': None,
        'motionEvents': 1,
        'spotifyStarted': True,
        'status': 'active'
    }
    dynamodb.put_item(table='Sessions', item=session)
    return session
```

**B. Update Session**
```python
def update_session(session_id):
    dynamodb.update_item(
        table='Sessions',
        key={'sessionId': session_id},
        update='SET motionEvents = motionEvents + 1, lastMotionTime = :now',
        values={':now': current_timestamp()}
    )
```

**C. End Session**
```python
def end_session(session_id):
    session = dynamodb.get_item('Sessions', session_id)
    duration = current_timestamp() - session['startTime']
    
    dynamodb.update_item(
        table='Sessions',
        key={'sessionId': session_id},
        update='SET endTime = :now, duration = :dur, status = :status',
        values={
            ':now': current_timestamp(),
            ':dur': duration,
            ':status': 'completed'
        }
    )
    
    # Update aggregated analytics
    update_daily_stats(session)
```

**D. Query Sessions**
```python
def query_sessions(sensor_id, start_date, end_date):
    return dynamodb.query(
        table='Sessions',
        index='SensorIdIndex',
        key_condition='sensorId = :id AND startTime BETWEEN :start AND :end',
        values={
            ':id': sensor_id,
            ':start': start_date,
            ':end': end_date
        }
    )
```

#### Function 5: Device Registration

**Trigger**: API Gateway POST /devices/register  
**Runtime**: Python 3.11  
**Timeout**: 30 seconds  
**Memory**: 256 MB

**Purpose**: Provision new IoT devices

**Input**:
```json
{
  "sensorId": "bedroom_sensor_01",
  "location": "Master Bedroom",
  "userId": "user_123"
}
```

**Logic Flow**:
```python
1. Validate input
2. Check if sensorId already exists
3. Create IoT Thing in AWS IoT Core
4. Generate X.509 certificate
5. Attach certificate to Thing
6. Attach IoT Policy to certificate
7. Create sensor record in DynamoDB
8. Return certificate and endpoint info
```

**Output**:
```json
{
  "sensorId": "bedroom_sensor_01",
  "thingArn": "arn:aws:iot:...",
  "certificateArn": "arn:aws:iot:...",
  "certificatePem": "-----BEGIN CERTIFICATE-----...",
  "privateKey": "-----BEGIN RSA PRIVATE KEY-----...",
  "iotEndpoint": "xxx.iot.us-east-1.amazonaws.com"
}
```

**Security Note**: Certificate and private key returned ONCE. User must save securely.

#### Function 6: API Handler

**Trigger**: API Gateway (all endpoints)  
**Runtime**: Python 3.11  
**Timeout**: 30 seconds  
**Memory**: 512 MB

**Purpose**: REST API for dashboard backend

**Endpoints**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/sensors` | List user's sensors |
| POST | `/sensors` | Create new sensor |
| GET | `/sensors/{id}` | Get sensor details |
| PUT | `/sensors/{id}` | Update sensor config |
| DELETE | `/sensors/{id}` | Delete sensor |
| GET | `/users/me` | Get user profile |
| PUT | `/users/me` | Update user preferences |
| GET | `/spotify/devices` | List Spotify devices |
| POST | `/spotify/test` | Test playback |
| GET | `/sessions` | Query sessions |
| GET | `/analytics` | Get statistics |

**Example Implementation** (GET /sensors):
```python
@app.get('/sensors')
def list_sensors(user_id: str):
    """List all sensors for authenticated user"""
    # user_id from Cognito JWT token
    
    sensors = dynamodb.query(
        table='Sensors',
        index='UserIdIndex',
        key_condition='userId = :id',
        values={':id': user_id}
    )
    
    return {
        'statusCode': 200,
        'body': {
            'sensors': sensors,
            'count': len(sensors)
        }
    }
```

**Authentication**: All endpoints require Cognito JWT token in Authorization header

**Error Responses**:
```json
{
  "statusCode": 400,
  "error": "ValidationError",
  "message": "sensorId is required",
  "requestId": "uuid"
}
```

### 3. Amazon DynamoDB

#### Table 1: Sensors

**Purpose**: Store sensor configuration

**Primary Key**: sensorId (String)

**Attributes**:
```python
{
    'sensorId': 'bathroom_main',              # PK
    'userId': 'user_123',                     # GSI
    'location': 'Main Bathroom',
    'spotifyDeviceId': 'device_abc',
    'playlistUri': 'spotify:playlist:...',
    'enabled': True,
    'lastMotionTime': 1704412800,
    'status': 'active',
    'preferences': {
        'timeoutMinutes': 5,
        'motionGapMinutes': 2,
        'quietHoursStart': '22:00',
        'quietHoursEnd': '07:00'
    },
    'createdAt': 1704412800,
    'updatedAt': 1704412800
}
```

**Indexes**:
- GSI: UserIdIndex (userId)

**Access Patterns**:
1. Get sensor by ID (single item)
2. List sensors by user (GSI query)
3. Update sensor configuration
4. Update last motion time (frequent write)

#### Table 2: Users

**Purpose**: Store user profiles and Spotify config

**Primary Key**: userId (String)

**Attributes**:
```python
{
    'userId': 'user_123',                     # PK
    'email': 'user@example.com',              # GSI
    'name': 'John Doe',
    'spotifyDevices': [
        {
            'deviceId': 'device_abc',
            'deviceName': 'Bathroom Speaker',
            'type': 'Speaker',
            'defaultPlaylist': 'spotify:playlist:...'
        }
    ],
    'preferences': {
        'globalTimeoutMinutes': 5,
        'globalMotionGapMinutes': 2,
        'quietHoursEnabled': True,
        'quietHoursStart': '22:00',
        'quietHoursEnd': '07:00',
        'notifications': {
            'email': True,
            'push': False
        }
    },
    'createdAt': 1704412800,
    'updatedAt': 1704412800
}
```

**Indexes**:
- GSI: EmailIndex (email)

**Access Patterns**:
1. Get user by ID
2. Get user by email (login)
3. Update user preferences
4. List all users (for token refresh)

#### Table 3: Sessions

**Purpose**: Track bathroom sessions for analytics

**Primary Key**: sessionId (String)

**Attributes**:
```python
{
    'sessionId': 'uuid',                      # PK
    'sensorId': 'bathroom_main',              # GSI
    'userId': 'user_123',
    'startTime': 1704412800,                  # GSI Sort Key
    'endTime': 1704413100,
    'duration': 300,                          # seconds
    'motionEvents': 5,
    'spotifyStarted': True,
    'playbackDuration': 280,                  # seconds
    'playlist': 'spotify:playlist:...',
    'status': 'completed',                    # active | completed | error
    'ttl': 1707004800                         # Auto-delete after 30 days
}
```

**Indexes**:
- GSI: SensorIdIndex (sensorId, startTime)

**TTL**: Auto-delete sessions older than 30 days

**Access Patterns**:
1. Get active session (sensorId + status=active)
2. Query sessions by date range
3. Calculate analytics (daily/weekly/monthly)

#### Table 4: MotionEvents

**Purpose**: Detailed motion event log for analytics

**Primary Key**: eventId (String)

**Attributes**:
```python
{
    'eventId': 'uuid',                        # PK
    'sensorId': 'bathroom_main',              # GSI
    'sessionId': 'uuid',
    'timestamp': 1704412800,                  # GSI Sort Key
    'action': 'motion_detected',              # motion_detected | timeout | manual_stop
    'metadata': {
        'batteryLevel': 85,
        'signalStrength': -45
    },
    'ttl': 1707004800                         # Auto-delete after 30 days
}
```

**Indexes**:
- GSI: SensorTimestampIndex (sensorId, timestamp)

**TTL**: Auto-delete events older than 30 days

**Access Patterns**:
1. Query events by sensor and time range
2. Generate usage heatmaps
3. Analyze motion patterns

### 4. AWS Secrets Manager

#### Secret 1: Spotify Client Credentials

**Name**: `spotty-potty-sense/spotify/client-credentials`

**Value**:
```json
{
  "client_id": "xxx",
  "client_secret": "yyy"
}
```

**Used By**: TokenRefresher, MotionHandler

#### Secret 2: User Refresh Tokens (per user)

**Name**: `spotty-potty-sense/spotify/users/{userId}/refresh-token`

**Value**:
```json
{
  "refresh_token": "zzz",
  "updated_at": "2026-01-04T12:00:00Z"
}
```

**Used By**: TokenRefresher, MotionHandler

#### Secret 3: User Access Tokens (cached, per user)

**Name**: `spotty-potty-sense/spotify/users/{userId}/access-token`

**Value**:
```json
{
  "access_token": "aaa",
  "expires_at": 1704416400,
  "updated_at": "2026-01-04T12:00:00Z"
}
```

**Used By**: MotionHandler, TimeoutChecker

**Rotation**: Automatic every 30 minutes via TokenRefresher

### 5. Amazon API Gateway

#### Configuration

- **Type**: REST API
- **Stage**: dev / staging / prod
- **Authorization**: Cognito User Pool
- **CORS**: Enabled for dashboard domain
- **Throttling**: 1000 requests/sec (dev), 10000 (prod)
- **Logging**: Full request/response logging to CloudWatch

#### Authorizer

**Type**: Cognito User Pool Authorizer

**Configuration**:
```yaml
Type: COGNITO_USER_POOLS
UserPoolArn: arn:aws:cognito-idp:...
IdentitySource: method.request.header.Authorization
```

**Token Validation**: Automatic by API Gateway

**User Context**: userId available to Lambda from JWT

#### Example Request

```bash
curl -X GET https://api.example.com/dev/sensors \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 6. Amazon Cognito

#### User Pool Configuration

**Password Policy**:
- Minimum length: 8 characters (dev), 12 (prod)
- Require uppercase, lowercase, numbers, symbols
- Password expiration: 90 days (prod)

**MFA**: Optional (prod: recommended)

**User Attributes**:
- email (required, verified)
- name (optional)
- custom:spotifyConnected (boolean)

**Sign-up**: Admin-created users only (for now)

**Sign-in**: Email + password

#### User Flow

1. **Sign Up** (Admin creates user)
   ```bash
   aws cognito-idp admin-create-user \
     --user-pool-id xxx \
     --username user@example.com \
     --user-attributes Name=email,Value=user@example.com
   ```

2. **First Login** (Set permanent password)
   - User receives temporary password via email
   - Must change on first login

3. **Spotify Authorization** (Dashboard)
   - User clicks "Connect Spotify"
   - OAuth flow → get refresh_token
   - Store in Secrets Manager
   - Update user profile

4. **Subsequent Logins**
   - Email + password
   - Receive JWT tokens (access + refresh + ID)
   - Store in browser localStorage
   - Refresh token before expiry

### 7. Dashboard (React Frontend)

#### Technology Stack

- **Framework**: React 18 with TypeScript
- **Build**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: Headless UI, Radix UI
- **State**: Zustand
- **API Client**: AWS Amplify
- **Auth**: AWS Amplify Auth
- **Charts**: Recharts
- **Icons**: Heroicons
- **Forms**: React Hook Form + Zod validation
- **Routing**: React Router v6

#### Pages

**1. Login (`/login`)**
- Email/password form
- "Forgot password" link
- Redirect to dashboard after login

**2. Dashboard Home (`/`)**
```tsx
// Components:
- SensorStatusCard (for each sensor)
  - Location name
  - Status indicator (active/idle)
  - Last motion time
  - Current playback info
- TodayStats
  - Total sessions
  - Total playback time
  - Most used sensor
- QuickActions
  - Test sensor
  - Manual play/pause
```

**3. Sensors (`/sensors`)**
```tsx
// Components:
- SensorList (table or cards)
  - Sensor ID
  - Location
  - Status
  - Last activity
  - Actions (edit, delete, test)
- AddSensorButton → Modal
  - Sensor ID (auto-generated or manual)
  - Location name
  - Linked Spotify device
  - Playlist selection
  - Timeout settings
```

**4. Analytics (`/analytics`)**
```tsx
// Components:
- DateRangePicker
- SessionsChart (line chart)
  - X-axis: Time (hourly/daily/weekly)
  - Y-axis: Number of sessions
- UsageHeatmap
  - X-axis: Hour of day (0-23)
  - Y-axis: Day of week
  - Color: Session count
- TopPlaylists (bar chart)
- StatsCards
  - Average session duration
  - Peak usage time
  - Total playback hours
```

**5. Spotify Devices (`/spotify`)**
```tsx
// Components:
- DeviceList
  - Device name
  - Device type (Speaker, Computer, Phone)
  - Status (online/offline)
  - Test playback button
- RefreshDevicesButton
  - Call Spotify API to get latest devices
```

**6. Settings (`/settings`)**
```tsx
// Tabs:
- Profile
  - Name, email (read-only)
  - Spotify account status
  - Re-authorize Spotify button
- Preferences
  - Global timeout minutes
  - Global motion gap minutes
  - Quiet hours toggle + time picker
  - Notification preferences
- Advanced
  - API usage stats
  - Export data (CSV)
  - Delete account
```

#### State Management

**User State** (Zustand):
```typescript
interface UserState {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}
```

**Sensors State**:
```typescript
interface SensorsState {
  sensors: Sensor[];
  loading: boolean;
  error: string | null;
  fetchSensors: () => Promise<void>;
  createSensor: (data: CreateSensorInput) => Promise<void>;
  updateSensor: (id: string, data: UpdateSensorInput) => Promise<void>;
  deleteSensor: (id: string) => Promise<void>;
}
```

#### API Client

```typescript
// src/services/api.ts
import { Amplify } from 'aws-amplify';

Amplify.configure({
  API: {
    endpoints: [
      {
        name: 'SpottyPottyAPI',
        endpoint: 'https://xxx.execute-api.us-east-1.amazonaws.com/dev',
        region: 'us-east-1'
      }
    ]
  },
  Auth: {
    region: 'us-east-1',
    userPoolId: 'us-east-1_xxx',
    userPoolWebClientId: 'xxx'
  }
});

// API functions
export const getSensors = async (): Promise<Sensor[]> => {
  const response = await API.get('SpottyPottyAPI', '/sensors', {
    headers: { Authorization: `Bearer ${await getToken()}` }
  });
  return response.sensors;
};
```

#### Deployment

**Hosting**: Amazon S3 + CloudFront

**Build Process**:
```bash
# Build
cd dashboard
npm run build

# Deploy to S3
aws s3 sync dist/ s3://spotty-potty-dashboard-prod/

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id E123456789 \
  --paths "/*"
```

---

## Data Models

### Sensor Entity

```typescript
interface Sensor {
  sensorId: string;              // PK: "bathroom_main"
  userId: string;                // FK to User
  location: string;              // "Main Bathroom"
  spotifyDeviceId: string;       // Spotify device ID
  playlistUri?: string;          // Optional playlist override
  enabled: boolean;              // Can disable without deleting
  lastMotionTime?: number;       // Unix timestamp
  status: 'active' | 'idle' | 'error';
  preferences: {
    timeoutMinutes: number;      // Stop after N minutes
    motionGapMinutes: number;    // Debounce: ignore motion if < N min since last
    quietHoursStart?: string;    // "22:00"
    quietHoursEnd?: string;      // "07:00"
  };
  metadata?: {
    deviceType: string;          // "ESP32", "Shelly", "Aqara"
    firmwareVersion?: string;
    batteryPowered?: boolean;
  };
  createdAt: number;
  updatedAt: number;
}
```

### User Entity

```typescript
interface User {
  userId: string;                // PK: "user_123"
  email: string;                 // "user@example.com"
  name?: string;                 // "John Doe"
  spotifyDevices: SpotifyDevice[];
  preferences: UserPreferences;
  createdAt: number;
  updatedAt: number;
}

interface SpotifyDevice {
  deviceId: string;
  deviceName: string;            // "Bathroom Speaker"
  type: string;                  // "Speaker", "Computer", "Smartphone"
  isActive: boolean;
  defaultPlaylist?: string;
}

interface UserPreferences {
  globalTimeoutMinutes: number;
  globalMotionGapMinutes: number;
  quietHoursEnabled: boolean;
  quietHoursStart?: string;
  quietHoursEnd?: string;
  notifications: {
    email: boolean;
    push: boolean;
  };
}
```

### Session Entity

```typescript
interface Session {
  sessionId: string;             // PK: UUID
  sensorId: string;              // FK to Sensor
  userId: string;                // FK to User
  startTime: number;             // Unix timestamp
  endTime?: number;              // Unix timestamp (null if active)
  duration?: number;             // Seconds (calculated on end)
  motionEvents: number;          // Count of motion detections
  spotifyStarted: boolean;       // Did we successfully start playback?
  playbackDuration?: number;     // Seconds (if available from Spotify)
  playlist?: string;             // Which playlist was played
  status: 'active' | 'completed' | 'error';
  errorMessage?: string;
  ttl: number;                   // Auto-delete timestamp (30 days)
}
```

### MotionEvent Entity

```typescript
interface MotionEvent {
  eventId: string;               // PK: UUID
  sensorId: string;              // FK to Sensor
  sessionId?: string;            // FK to Session (if linked)
  timestamp: number;             // Unix timestamp
  action: 'motion_detected' | 'timeout' | 'manual_stop';
  metadata?: {
    batteryLevel?: number;       // 0-100
    signalStrength?: number;     // dBm
    temperature?: number;        // Celsius
  };
  ttl: number;                   // Auto-delete timestamp (30 days)
}
```

---

## API Specifications

### Base URL

- **Development**: `https://xxx.execute-api.us-east-1.amazonaws.com/dev`
- **Production**: `https://api.spottypotty.com` (custom domain)

### Authentication

All endpoints require Bearer token (Cognito JWT):

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Endpoints

#### Sensors

**GET /sensors**

List all sensors for authenticated user.

Response:
```json
{
  "sensors": [
    {
      "sensorId": "bathroom_main",
      "location": "Main Bathroom",
      "enabled": true,
      "status": "active",
      "lastMotionTime": 1704412800
    }
  ],
  "count": 1
}
```

**POST /sensors**

Create new sensor.

Request:
```json
{
  "sensorId": "bedroom_01",
  "location": "Master Bedroom",
  "spotifyDeviceId": "device_xyz",
  "playlistUri": "spotify:playlist:...",
  "preferences": {
    "timeoutMinutes": 10
  }
}
```

Response:
```json
{
  "sensor": { ... },
  "message": "Sensor created successfully"
}
```

**PUT /sensors/{id}**

Update sensor configuration.

**DELETE /sensors/{id}**

Delete sensor (soft delete: set enabled=false).

#### Users

**GET /users/me**

Get current user profile.

**PUT /users/me**

Update user preferences.

#### Spotify

**GET /spotify/devices**

List available Spotify devices for user.

Response:
```json
{
  "devices": [
    {
      "id": "device_abc",
      "name": "Bathroom Speaker",
      "type": "Speaker",
      "is_active": false,
      "volume_percent": 50
    }
  ]
}
```

**POST /spotify/test**

Test playback on a device.

Request:
```json
{
  "deviceId": "device_abc"
}
```

#### Sessions & Analytics

**GET /sessions**

Query sessions with filters.

Query Parameters:
- `sensorId` (optional)
- `startDate` (ISO 8601)
- `endDate` (ISO 8601)
- `limit` (default: 50)
- `nextToken` (pagination)

**GET /analytics**

Get aggregated statistics.

Query Parameters:
- `period`: `day` | `week` | `month`
- `startDate`
- `endDate`

Response:
```json
{
  "totalSessions": 120,
  "totalPlaybackTime": 36000,
  "averageSessionDuration": 300,
  "peakUsageHour": 8,
  "topSensor": "bathroom_main",
  "dailyBreakdown": [
    { "date": "2026-01-01", "sessions": 12 },
    ...
  ]
}
```

---

## Security Architecture

### Authentication & Authorization

**User Authentication**: Amazon Cognito
- Email/password authentication
- JWT tokens (access, ID, refresh)
- Token expiration: 1 hour
- Refresh token valid: 30 days

**Device Authentication**: AWS IoT Core
- X.509 certificates (unique per device)
- Certificate-based mutual TLS
- Policy-based authorization

### Secrets Management

**AWS Secrets Manager**:
- Spotify client credentials
- User refresh tokens
- User access tokens (cached)

**Encryption**:
- At rest: AWS KMS encryption
- In transit: TLS 1.2+

**Access Control**:
- Lambda execution roles (least privilege)
- No secrets in environment variables
- No secrets in logs

### IAM Policies

**Lambda Execution Role** (example):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/SpottyPottySense-Sensors-dev",
        "arn:aws:dynamodb:us-east-1:123456789012:table/SpottyPottySense-Sensors-dev/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:spotty-potty-sense/spotify/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/SpottyPottySense-*"
    }
  ]
}
```

### Network Security

**API Gateway**:
- HTTPS only (TLS 1.2+)
- CORS configured for dashboard domain only
- Rate limiting (throttling)
- AWS WAF (optional, for DDoS protection)

**IoT Core**:
- MQTTS (port 8883)
- X.509 certificate authentication
- No anonymous connections
- Topic-based authorization

### Data Protection

**DynamoDB**:
- Encryption at rest (AWS-managed keys)
- Point-in-time recovery enabled
- Backups configured

**CloudWatch Logs**:
- Encrypted
- No PII or secrets logged
- Retention: 30 days (dev), 90 days (prod)

### Compliance

**GDPR Considerations**:
- User data deletion capability
- Data export (API)
- Audit logs
- Data retention policies (TTL)

---

## Implementation Plan

### Phase 0: Prerequisites & Setup ✅ COMPLETE

- [x] AWS Account setup
- [x] Spotify Developer account
- [x] Configure OAuth redirect URIs
- [x] Generate Spotify refresh token
- [x] Test Spotify API access
- [x] Install AWS CLI, SAM CLI
- [x] Create project structure
- [x] Initialize Git repository

### Phase 1: Infrastructure Foundation ✅ COMPLETE

- [x] Create SAM template with all resources
- [x] Define DynamoDB tables
- [x] Define Lambda function stubs
- [x] Configure IoT Core policy
- [x] Set up API Gateway
- [x] Configure Cognito User Pool
- [x] Create deployment scripts
- [x] Write comprehensive documentation

**Deliverable**: Deployable infrastructure template

### Phase 2: Backend Implementation (2-3 weeks)

#### Week 1: Core Lambda Functions

**Task 2.1: Common Layer**
```
Files to create:
- backend/src/layers/common/python/spotify_client.py
- backend/src/layers/common/python/dynamodb_helper.py
- backend/src/layers/common/python/secrets_helper.py
- backend/src/layers/common/python/validation.py
- backend/src/layers/common/python/exceptions.py
- backend/src/layers/common/python/logger.py

Implementation:
1. spotify_client.py:
   - SpotifyClient class
   - refresh_token() method
   - start_playback(device_id, playlist) method
   - pause_playback(device_id) method
   - get_devices() method
   - Retry logic with exponential backoff
   - Error handling

2. dynamodb_helper.py:
   - DynamoDBHelper class
   - get_item(table, key) method
   - put_item(table, item) method
   - update_item(table, key, updates) method
   - query(table, index, condition) method
   - Batch operations

3. secrets_helper.py:
   - SecretsHelper class
   - get_secret(name) method
   - update_secret(name, value) method
   - Cache secrets (in-memory for Lambda warm starts)

4. validation.py:
   - Pydantic models for all entities
   - validate_sensor(data) function
   - validate_user(data) function
   - validate_session(data) function

5. exceptions.py:
   - SpotifyAPIError
   - DynamoDBError
   - ValidationError
   - ConfigurationError

6. logger.py:
   - Structured JSON logging
   - Context injection (requestId, userId, etc.)
   - Log levels based on environment

Testing:
- Unit tests for each module
- Mock AWS services (moto library)
- Mock Spotify API
- Achieve >80% code coverage
```

**Task 2.2: Token Refresher Function**
```
File: backend/src/functions/token-refresher/index.py

Implementation:
1. handler(event, context):
   - Get all users from DynamoDB
   - For each user:
     * Get refresh_token from Secrets Manager
     * Call Spotify token endpoint
     * Update access_token in Secrets Manager
   - Log success/failures
   - Return summary

2. Error handling:
   - Retry on network errors
   - Alert if refresh_token is invalid
   - Continue processing other users if one fails

Testing:
- Unit tests with mocked dependencies
- Integration test with real DynamoDB (local)
- Test error scenarios

Deployment:
- Deploy individually: sam build TokenRefresherFunction && sam deploy
- Test with: sam remote invoke TokenRefresherFunction
```

**Task 2.3: Motion Handler Function**
```
File: backend/src/functions/motion-handler/index.py

Implementation:
1. handler(event, context):
   - Parse IoT event
   - Validate sensorId exists
   - Get sensor config
   - Get user config
   - Check quiet hours
   - Check debounce
   - Get Spotify token
   - Get or create session
   - Start Spotify playback
   - Update DynamoDB
   - Schedule timeout check

2. Helper functions:
   - is_quiet_hours(config, timestamp)
   - should_debounce(last_motion, gap_minutes)
   - get_or_create_session(sensor_id)

Testing:
- Unit tests for all logic paths
- Integration test with DynamoDB
- Mock Spotify API
- Test quiet hours logic
- Test debounce logic

Deployment:
- Deploy and test with IoT test client
```

#### Week 2: Supporting Functions

**Task 2.4: Timeout Checker Function**

**Task 2.5: Session Manager Function**

**Task 2.6: Device Registration Function**

#### Week 3: API Handler

**Task 2.7: API Handler Function**
```
All REST API endpoints
Input validation
Error handling
Pagination
```

**Task 2.8: Integration Testing**
```
End-to-end tests
Load testing
Security testing
```

### Phase 3: IoT Device Integration (1 week)

**Task 3.1: Choose Device**
- Evaluate options (ESP32, Shelly, Aqara)
- Order hardware

**Task 3.2: Device Firmware** (if ESP32)
```
File: device-firmware/src/main.cpp

Implementation:
1. Setup:
   - Initialize WiFi
   - Load certificates from SPIFFS
   - Connect to AWS IoT Core
   - Subscribe to config topic

2. Loop:
   - Check for motion (PIR interrupt)
   - Debounce in firmware
   - Publish to sensors/{id}/motion
   - Handle incoming config updates

3. Features:
   - OTA updates
   - LED status indicators
   - Deep sleep for battery
   - Reconnection logic

Testing:
- Test WiFi connection
- Test IoT connection
- Test motion detection
- Test certificate auth
```

**Task 3.3: Device Provisioning**
```
Script: scripts/provision-device.sh

1. Generate certificate via API
2. Flash firmware to device
3. Upload certificate to device
4. Test connection
5. Add sensor to DynamoDB
```

### Phase 4: Frontend Dashboard (2 weeks)

**Task 4.1: Project Setup**
```
cd dashboard
npm create vite@latest . -- --template react-ts
npm install tailwindcss aws-amplify zustand react-router-dom recharts
Configure Tailwind, Amplify
```

**Task 4.2: Authentication**
```
Pages:
- Login
- Password reset
Components:
- Auth wrapper
- Protected routes
```

**Task 4.3: Core Pages**
```
Week 1:
- Dashboard home
- Sensors list
- Sensor CRUD

Week 2:
- Analytics
- Settings
- Spotify devices
```

**Task 4.4: Styling & UX**
```
- Responsive design
- Loading states
- Error handling
- Toast notifications
```

**Task 4.5: Deployment**
```
- Build production bundle
- Deploy to S3
- Configure CloudFront
- Test
```

### Phase 5: Testing & QA (1 week)

**Task 5.1: Unit Testing**
- All Lambda functions
- Frontend components

**Task 5.2: Integration Testing**
- End-to-end flow
- API tests
- IoT tests

**Task 5.3: Load Testing**
- Concurrent requests
- Lambda concurrency
- DynamoDB throughput

**Task 5.4: Security Testing**
- Penetration testing (basic)
- OWASP Top 10
- IAM policy review

**Task 5.5: User Acceptance Testing**
- Real-world usage
- Bug fixes

### Phase 6: Deployment & Launch (3 days)

**Task 6.1: Production Deployment**
```
# Deploy backend
./scripts/deploy.sh prod

# Deploy frontend
cd dashboard && npm run build
aws s3 sync dist/ s3://spotty-potty-dashboard-prod/
aws cloudfront create-invalidation --distribution-id xxx --paths "/*"
```

**Task 6.2: Monitoring Setup**
- CloudWatch dashboards
- Alarms
- SNS notifications

**Task 6.3: Documentation**
- User guide
- API documentation
- Troubleshooting guide

### Phase 7: Post-Launch (Ongoing)

**Task 7.1: Monitoring**
- Daily log review
- Weekly cost review
- Monthly analytics

**Task 7.2: Optimization**
- Lambda performance tuning
- Cost optimization
- User feedback implementation

---

## Testing Strategy

### Unit Testing

**Backend (Python)**:
```python
# pytest framework
# File: backend/tests/unit/test_motion_handler.py

import pytest
from moto import mock_dynamodb, mock_secretsmanager
from functions.motion_handler import handler

@mock_dynamodb
@mock_secretsmanager
def test_motion_handler_success():
    # Setup mocks
    # ...
    
    # Test
    event = {...}
    response = handler(event, {})
    
    # Assert
    assert response['statusCode'] == 200
    assert 'sessionId' in response
```

**Frontend (React)**:
```typescript
// Jest + React Testing Library
// File: dashboard/src/components/__tests__/SensorCard.test.tsx

import { render, screen } from '@testing-library/react';
import { SensorCard } from '../SensorCard';

test('renders sensor information', () => {
  const sensor = { sensorId: 'test', location: 'Test' };
  render(<SensorCard sensor={sensor} />);
  expect(screen.getByText('Test')).toBeInTheDocument();
});
```

### Integration Testing

**Backend API Tests**:
```python
# pytest with real AWS services (dev environment)
# File: backend/tests/integration/test_api_flow.py

def test_create_sensor_flow():
    # 1. Create sensor via API
    response = requests.post(API_URL + '/sensors', json={...})
    assert response.status_code == 200
    
    # 2. Verify in DynamoDB
    sensor = dynamodb.get_item(...)
    assert sensor is not None
    
    # 3. Query via API
    response = requests.get(API_URL + '/sensors')
    assert len(response.json()['sensors']) == 1
```

### End-to-End Testing

**Complete Flow**:
```
1. Device publishes motion event to IoT Core
2. Wait for Lambda execution
3. Check CloudWatch logs
4. Verify session created in DynamoDB
5. Check Spotify playback status
6. Wait for timeout
7. Verify playback stopped
8. Verify session ended
```

### Load Testing

**Tools**: Artillery, Locust, or AWS Load Testing

```yaml
# artillery config
config:
  target: 'https://api.example.com/dev'
  phases:
    - duration: 60
      arrivalRate: 10
scenarios:
  - name: 'Get sensors'
    flow:
      - get:
          url: '/sensors'
          headers:
            Authorization: 'Bearer {token}'
```

---

## Deployment Guide

### Prerequisites

```bash
# Install tools
brew install aws-cli aws-sam-cli python node

# Configure AWS
aws configure
# Enter: Access Key, Secret Key, Region (us-east-1)

# Verify
aws sts get-caller-identity
```

### First-Time Deployment

**Step 1: Deploy Infrastructure**
```bash
# Build
sam build --parallel

# Deploy (interactive)
sam deploy --guided

# Answer prompts:
# Stack Name: spotty-potty-sense-dev
# AWS Region: us-east-1
# Parameter Environment: dev
# Confirm changes: Y
# Allow SAM CLI IAM role creation: Y
# Save arguments to config: Y
```

**Step 2: Store Secrets**
```bash
./scripts/setup-secrets.sh dev
```

**Step 3: Create Cognito User**
```bash
# Get User Pool ID from stack outputs
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name spotty-potty-sense-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)

# Create user
aws cognito-idp admin-create-user \
  --user-pool-id ${USER_POOL_ID} \
  --username your.email@example.com \
  --user-attributes Name=email,Value=your.email@example.com Name=email_verified,Value=true \
  --temporary-password TempPass123!
```

**Step 4: Add User to DynamoDB**
```bash
# Create user record
aws dynamodb put-item \
  --table-name SpottyPottySense-Users-dev \
  --item '{
    "userId": {"S": "user_default"},
    "email": {"S": "your.email@example.com"},
    "preferences": {"M": {
      "globalTimeoutMinutes": {"N": "5"},
      "globalMotionGapMinutes": {"N": "2"}
    }},
    "createdAt": {"N": "'$(date +%s)'"}
  }'
```

**Step 5: Deploy Dashboard**
```bash
cd dashboard

# Build
npm run build

# Create S3 bucket (one-time)
aws s3 mb s3://spotty-potty-dashboard-dev

# Deploy
aws s3 sync dist/ s3://spotty-potty-dashboard-dev/ --delete

# Make public (if not using CloudFront)
aws s3 website s3://spotty-potty-dashboard-dev/ \
  --index-document index.html \
  --error-document index.html
```

### Subsequent Deployments

```bash
# Backend only
./scripts/deploy.sh dev

# Frontend only
cd dashboard && npm run build
aws s3 sync dist/ s3://spotty-potty-dashboard-dev/ --delete

# Both
./scripts/deploy.sh dev
cd dashboard && npm run build
aws s3 sync dist/ s3://spotty-potty-dashboard-dev/ --delete
```

### Environment Promotion

```bash
# Deploy to staging
./scripts/deploy.sh staging

# Deploy to production (with confirmation)
./scripts/deploy.sh prod
```

---

## Cost Analysis

### Monthly Cost Breakdown (Single User, 30 motion events/day)

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **IoT Core** | 900 messages | $1.00 / million | $0.001 |
| **Lambda Invocations** | 10,000 | $0.20 / million | $0.002 |
| **Lambda Compute** | 10K * 256MB * 0.1s | $0.0000166667 / GB-sec | $0.004 |
| **DynamoDB Reads** | 30K (pay-per-request) | $0.25 / million | $0.0075 |
| **DynamoDB Writes** | 10K (pay-per-request) | $1.25 / million | $0.0125 |
| **DynamoDB Storage** | 0.1 GB | $0.25 / GB | $0.025 |
| **Secrets Manager** | 3 secrets | $0.40 / secret | $1.20 |
| **API Gateway** | 1,000 requests | $1.00 / million | $0.001 |
| **CloudWatch Logs** | 0.5 GB | $0.50 / GB | $0.25 |
| **CloudWatch Metrics** | 10 custom | $0.30 / metric | $3.00 |
| **S3 Storage** | 0.1 GB | $0.023 / GB | $0.002 |
| **CloudFront** | 1 GB transfer | $0.085 / GB | $0.085 |
| **X-Ray** | 10K traces | $5.00 / million | $0.05 |
| **Cognito** | 1 MAU | Free tier | $0.00 |
| **EventBridge** | 50K events | $1.00 / million | $0.05 |
| **TOTAL** | | | **~$4.70/month** |

### Cost Optimization Tips

1. **Use Free Tier**: Most services have generous free tiers
2. **DynamoDB On-Demand**: Better than provisioned for low traffic
3. **Lambda Memory**: 256MB is sweet spot (more = faster = cheaper)
4. **Log Retention**: 30 days in dev, 7 days in prod after archival
5. **CloudWatch Metrics**: Only create essential custom metrics
6. **S3 Lifecycle**: Move old logs to Glacier after 90 days
7. **Reserved Capacity**: Consider if usage grows significantly

### Scaling Cost Estimates

| Users | Devices | Monthly Cost |
|-------|---------|--------------|
| 1 | 1 | $4.70 |
| 1 | 5 | $6.20 |
| 5 | 10 | $12.50 |
| 10 | 20 | $22.00 |
| 100 | 200 | $180.00 |

**Note**: Costs scale sub-linearly due to shared infrastructure (API, Cognito, etc.)

---

## Future Enhancements

### Phase 8: Advanced Features

**1. Voice Control via Alexa**
- Create Alexa Skill
- "Alexa, play bathroom music"
- "Alexa, stop bathroom music"

**2. Machine Learning**
- Predict bathroom visits based on time patterns
- Suggest playlists based on time of day
- Anomaly detection (unusual patterns = alert)

**3. Multi-Room Coordination**
- Seamless handoff between rooms
- "Follow me" mode
- Synchronized playback

**4. Presence Detection**
- Bluetooth beacons for user identification
- Multiple users → personalized playlists
- Smartphone proximity detection

**5. Home Assistant Integration**
- HASS.io plugin
- Unified smart home control
- Automation triggers

**6. Mobile App**
- React Native app
- Push notifications
- Quick controls
- Offline mode

**7. Advanced Analytics**
- Predictive analytics
- Comparative benchmarks
- Social features (compare with friends)
- Insights and recommendations

**8. Integrations**
- IFTTT webhooks
- Zapier integration
- Discord/Slack notifications
- Google Calendar (quiet hours during meetings)

### Phase 9: Enterprise Features

**1. Multi-Tenant**
- Support multiple households
- Per-household billing
- Admin dashboard

**2. Marketplace**
- Community-created integrations
- Plugin system
- Playlist marketplace

**3. API**
- Public API for third-party apps
- API keys and rate limiting
- Developer portal

---

## Conclusion

This document provides a complete technical specification for re-architecting SpottyPottySense from a Raspberry Pi-based system to an enterprise-grade AWS serverless application.

### Key Takeaways

1. **Serverless = Better**: No servers to manage, auto-scaling, pay-per-use
2. **AWS Native**: Leverage managed services for reliability
3. **Security First**: Certificates, encryption, least privilege
4. **Observable**: Comprehensive logging and monitoring
5. **Scalable**: From 1 to millions of devices
6. **Cost-Effective**: $2-5/month vs. $10-15 for old setup
7. **Maintainable**: Infrastructure as Code, automated deployments

### Success Metrics

- ✅ 99.9% uptime (vs. 95% with Raspberry Pi)
- ✅ <1 second latency (motion → playback)
- ✅ <$5/month operational cost
- ✅ Zero manual maintenance
- ✅ Support 10+ sensors
- ✅ Support multiple users
- ✅ Web dashboard with analytics

### Getting Started

1. Review this document thoroughly
2. Set up AWS account and prerequisites
3. Follow Phase 1 (infrastructure) - **COMPLETE ✅**
4. Implement Phase 2 (Lambda functions)
5. Deploy and test each component incrementally
6. Build dashboard (Phase 4)
7. Launch and iterate

### Support & Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **Spotify API**: https://developer.spotify.com/documentation/web-api/
- **Project Repository**: https://github.com/yourusername/SpottyPottySense
- **SAM CLI Guide**: https://docs.aws.amazon.com/serverless-application-model/

---

**Document Version**: 2.0  
**Last Updated**: January 4, 2026  
**Status**: Ready for Implementation  

Good luck building SpottyPottySense v2.0! 🎵🚀

