# Spotify Integration Setup Guide

Complete guide to connect your SpottyPottySense system to Spotify.

## Prerequisites

- ✅ Backend deployed to AWS
- ✅ ESP8266 sensor connected to AWS IoT
- 🎵 Active Spotify Premium account (required for playback control)

---

## Step 1: Create Spotify Developer App

### 1.1 Register Application

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click **"Create app"**

**Fill in the form:**
- **App name**: `SpottyPottySense`
- **App description**: `IoT-based bathroom music automation`
- **Redirect URI**: `http://127.0.0.1:8888/callback`
- **Which API/SDKs are you planning to use?**: Web API
- Check the terms and conditions box
- Click **"Save"**

### 1.2 Get Credentials

After creating the app:
1. Click **"Settings"** button
2. Copy your **Client ID** (looks like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`)
3. Click **"View client secret"** and copy it
4. **Save these securely** - you'll need them in Step 3

### 1.3 Configure Scopes

Your app needs these permissions:
- `user-read-playback-state` - Check what's playing
- `user-modify-playback-state` - Start/pause music
- `user-read-currently-playing` - Get current track

(These are set when you request the OAuth token)

---

## Step 2: Store Spotify Client Credentials in AWS

Store your app's Client ID and Secret:

```bash
aws secretsmanager create-secret \
  --name "spotty-potty-sense/spotify/client" \
  --description "Spotify app client credentials" \
  --secret-string '{
    "client_id": "YOUR_CLIENT_ID_HERE",
    "client_secret": "YOUR_CLIENT_SECRET_HERE"
  }' \
  --region us-east-2
```

**Verify it was created:**
```bash
aws secretsmanager get-secret-value \
  --secret-id "spotty-potty-sense/spotify/client" \
  --region us-east-2 \
  --query SecretString \
  --output text
```

---

## Step 3: Get Spotify OAuth Tokens

Run the helper script to authenticate and get your tokens:

```bash
./scripts/setup-spotify-oauth.sh
```

**What it does:**
1. Starts a local web server on port 8888
2. Opens browser to Spotify authorization page
3. You log in and approve permissions
4. Captures the authorization code
5. Exchanges it for refresh/access tokens
6. Automatically stores tokens in AWS Secrets Manager

**Output:**
```
🎵 SpottyPottySense Spotify OAuth Setup
========================================

✓ Retrieved Spotify client credentials from AWS Secrets Manager
✓ Starting local callback server on http://127.0.0.1:8888

Opening browser for Spotify authorization...
Please log in and approve permissions.

Waiting for callback...

✓ Authorization code received!
✓ Token exchange successful!
✓ Tokens stored in AWS Secrets Manager

Your user ID: spotify:user:yourusername

Next steps:
1. Register your sensor using ./scripts/register-sensor.sh
```

---

## Step 4: Create Cognito User Account

Create your user account in Cognito:

```bash
./scripts/create-user.sh
```

**You'll be prompted for:**
- Email address
- Temporary password (you'll change on first login)

**Output:**
```
✓ User created: user-abc123
✓ Confirmation email sent

Save this User ID: user-abc123
(You'll need it for sensor registration)
```

---

## Step 5: Get Your Spotify Device ID

Find which Spotify device (speaker/computer) to play on:

```bash
./scripts/list-spotify-devices.sh
```

**Output:**
```
Available Spotify Devices:
==========================

1. MacBook Pro
   ID: 5fbb3ba6aa454b5534c4ba43a8c7e8e45a63ad0e
   Type: Computer
   Active: Yes

2. Sonos Bathroom
   ID: 7e8c9d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e
   Type: Speaker
   Active: No

Enter device number to copy ID: 2
✓ Copied: 7e8c9d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e
```

---

## Step 6: Register Your Sensor with Full Config

Now register your sensor with all the Spotify details:

```bash
./scripts/register-sensor.sh
```

**Interactive prompts:**
```
Sensor ID [bathroom-main]: bathroom-main
Location [Main Bathroom]: Main Bathroom
User ID: user-abc123
Spotify Device ID: 7e8c9d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e
Playlist URI [optional]: spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
Timeout Minutes [5]: 5
Motion Debounce Minutes [2]: 2
```

**Output:**
```
✓ Sensor registered successfully!
✓ Configuration saved to DynamoDB

Summary:
--------
Sensor ID: bathroom-main
User ID: user-abc123
Spotify Device: Sonos Bathroom
Playlist: Daily Mix 1
Timeout: 5 minutes
Debounce: 2 minutes

Ready to test! Trigger motion to start Spotify.
```

---

## Step 7: Test End-to-End

### 7.1 Trigger Motion
Wave your hand in front of the PIR sensor.

### 7.2 Check Serial Monitor
```
[MOTION] Detected! Publishing event...
[MQTT] ✓ Motion event published
```

### 7.3 Check Spotify
Within 2-3 seconds, **Spotify should start playing** on your configured device!

### 7.4 Verify Logs
```bash
# Check Lambda logs
aws logs tail /aws/lambda/spotty-potty-sense-MotionHandlerFunction --follow --region us-east-2

# Check DynamoDB sessions
aws dynamodb scan \
  --table-name spotty-potty-sense-SessionsTable-* \
  --filter-expression "#status = :status" \
  --expression-attribute-names '{"#status":"status"}' \
  --expression-attribute-values '{":status":{"S":"active"}}' \
  --region us-east-2
```

---

## Troubleshooting

### Spotify Doesn't Play

**1. Check device is available:**
```bash
./scripts/list-spotify-devices.sh
```
- Ensure device is online and visible

**2. Check tokens are valid:**
```bash
aws secretsmanager get-secret-value \
  --secret-id "spotty-potty-sense/spotify/users/YOUR_USER_ID" \
  --region us-east-2
```
- Verify `expires_at` is in the future
- Token Refresher runs every 30 minutes

**3. Check Lambda logs:**
- Look for Spotify API errors (401 = bad token, 404 = device not found)

### Motion Detected But Lambda Not Triggered

**Check IoT Rule:**
```bash
aws iot get-topic-rule \
  --rule-name SpottyPottySenseMotionRule \
  --region us-east-2
```
- Verify SQL: `SELECT * FROM 'sensors/+/motion'`
- Verify action points to MotionHandlerFunction

### Sensor Not Found Error

Sensor must be registered first:
```bash
# Check if sensor exists
aws dynamodb get-item \
  --table-name spotty-potty-sense-SensorsTable-* \
  --key '{"sensorId":{"S":"bathroom-main"}}' \
  --region us-east-2
```

---

## Summary

**Setup checklist:**
- [ ] Spotify Developer App created
- [ ] Client credentials in Secrets Manager
- [ ] OAuth tokens obtained and stored
- [ ] Cognito user created
- [ ] Spotify device ID identified
- [ ] Sensor registered with full config
- [ ] Motion detection triggers Spotify ✨

**Next:** Use the helper scripts in `scripts/` to complete each step!
