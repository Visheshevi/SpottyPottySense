# 🎵 Complete Spotify Setup Guide

Follow these steps in order to get SpottyPottySense fully operational with Spotify.

---

## 📋 Overview

You'll complete these 5 steps:
1. **Create Spotify Developer App** (5 minutes)
2. **Store credentials in AWS** (2 minutes)
3. **Authenticate with Spotify** (3 minutes)
4. **Get your Spotify device ID** (2 minutes)
5. **Register sensor with full config** (3 minutes)

**Total time: ~15 minutes**

---

## Step 1: Create Spotify Developer App (5 min)

### 1.1 Go to Spotify Developer Dashboard
Open: https://developer.spotify.com/dashboard

### 1.2 Create New App
- Click **"Create app"**
- **App name**: `SpottyPottySense`
- **App description**: `IoT bathroom music automation`
- **Redirect URI**: `http://127.0.0.1:8888/callback` ← **IMPORTANT**
- **API**: Web API
- Agree to terms → **Save**

### 1.3 Get Your Credentials
- Click **"Settings"**
- Copy **Client ID** (save it)
- Click **"View client secret"** → Copy it (save it)

✅ **You now have:**
- Client ID: `abc123...`
- Client Secret: `xyz789...`

---

## Step 2: Store Credentials in AWS (2 min)

Run this command with YOUR credentials:

```bash
aws secretsmanager create-secret \
  --name "spotty-potty-sense/spotify/client" \
  --description "Spotify app client credentials" \
  --secret-string '{
    "client_id": "PASTE_YOUR_CLIENT_ID_HERE",
    "client_secret": "PASTE_YOUR_CLIENT_SECRET_HERE"
  }' \
  --region us-east-2
```

**Verify it worked:**
```bash
aws secretsmanager get-secret-value \
  --secret-id "spotty-potty-sense/spotify/client" \
  --region us-east-2 \
  --query SecretString \
  --output text | python3 -m json.tool
```

Should show your client_id and client_secret.

---

## Step 3: Authenticate with Spotify (3 min)

Run the OAuth helper script:

```bash
./scripts/setup-spotify-oauth.sh
```

**What happens:**
1. Script retrieves your client credentials from AWS
2. Opens browser to Spotify login page
3. You log in with your **Spotify Premium** account
4. Approve permissions
5. Script captures tokens and stores them in AWS Secrets Manager
6. Creates user record in DynamoDB

**You'll see:**
```
🎵 SpottyPottySense Spotify OAuth Setup
========================================

✓ Retrieved Spotify client credentials
✓ Starting local callback server on http://127.0.0.1:8888

Opening browser for Spotify authorization...
[Browser opens]

✓ Authorization code received!
✓ Token exchange successful!
✓ Tokens stored in AWS Secrets Manager

Your User ID: user-abc123-def456-...

Next steps:
1. List your Spotify devices: ./scripts/list-spotify-devices.sh
```

**Save your User ID!** You'll need it for the next steps.

---

## Step 4: Get Spotify Device ID (2 min)

Find which device (speaker/computer) to play music on:

```bash
./scripts/list-spotify-devices.sh
```

**Enter your User ID** (from Step 3)

**You'll see:**
```
🔊 Available Spotify Devices
============================

Found 3 device(s):

1. MacBook Pro
   ID: 5fbb3ba6aa454b5534c4ba43a8c7e8e45a63ad0e
   Type: Computer
   Active: Yes

2. Sonos Bathroom Speaker
   ID: 7e8c9d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e
   Type: Speaker
   Active: No

3. iPhone
   ID: 9f8e7d6c5b4a3d2e1f0a9b8c7d6e5f4a3b2c1d0e
   Type: Smartphone
   Active: No

Enter device number to copy ID: 2
✓ Copied: 7e8c9d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e
```

**Pick the device** you want music to play on (usually your bathroom speaker).

**Device ID is copied to clipboard!**

---

## Step 5: Register Sensor with Full Config (3 min)

Now connect everything together:

```bash
./scripts/register-sensor.sh
```

**You'll be prompted for:**
```
Sensor ID [bathroom-main]: bathroom-main
Location [Main Bathroom]: Main Bathroom
Sensor Name [bathroom-main]: Bathroom Motion Sensor
User ID: user-abc123-def456-...  ← from Step 3
Spotify Device ID: 7e8c9d...     ← paste from Step 4
Playlist URI [default]: spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
Timeout Minutes [5]: 5
Motion Debounce Minutes [2]: 2

Proceed with registration? (y/n): y
```

**Success output:**
```
✓ Sensor registered successfully!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Registration Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sensor ID:       bathroom-main
Location:        Main Bathroom
User ID:         user-abc123-def456-...
Spotify Device:  7e8c9d0a1b2c3d4e5f6a...
Playlist:        Daily Mix 1
Timeout:         5 minutes
Debounce:        2 minutes

🎉 Ready to test! Trigger motion on your ESP8266 sensor.
```

---

## Step 6: Test! 🎉

### 6.1 Trigger Motion
Wave your hand in front of PIR sensor.

### 6.2 Watch Multiple Places

**A. Serial Monitor (ESP8266):**
```
[MOTION] Detected! Publishing event...
[MQTT] ✓ Motion event published
```

**B. AWS IoT MQTT Test Client:**
- Subscribe to: `sensors/bathroom-main/motion`
- Should see JSON message

**C. Lambda Logs:**
```bash
aws logs tail /aws/lambda/spotty-potty-sense-MotionHandlerFunction \
  --follow --region us-east-2
```

Should show:
```
[INFO] Motion event received from sensor: bathroom-main
[INFO] User: user-abc123...
[INFO] Starting Spotify playback on device: Sonos Bathroom
[INFO] ✓ Playback started successfully
```

**D. Spotify App:**
- **Music should start playing** on your configured device! 🎶

### 6.3 Test Timeout
- Stop moving for 5 minutes
- Spotify should **automatically pause**
- Check timeout checker logs:
```bash
aws logs tail /aws/lambda/spotty-potty-sense-TimeoutCheckerFunction \
  --follow --region us-east-2
```

---

## 🎵 Popular Playlist URIs

Instead of the default, try these Spotify playlists:

```
Daily Mix 1:          spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
Today's Top Hits:     spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
Peaceful Piano:       spotify:playlist:37i9dQZF1DX4sWSpwq3LiO
Chill Hits:           spotify:playlist:37i9dQZF1DX4WYpdgoIcn6
Rock Classics:        spotify:playlist:37i9dQZF1DWXRqgorJj26U
```

**To find any playlist URI:**
1. Open Spotify app
2. Right-click playlist → Share → Copy Spotify URI
3. Paste when registering sensor

---

## Troubleshooting

### "No devices found"
- **Spotify app must be open** on at least one device
- **Premium account required** (Free tier can't control playback)
- Refresh by opening Spotify and playing any song, then stop it

### "401 Unauthorized" in Lambda logs
- Token expired → Token Refresher runs every 30 minutes
- Wait 30 min or manually invoke TokenRefresherFunction

### Spotify plays but wrong device
- Re-run `./scripts/register-sensor.sh`
- Update with correct Spotify Device ID

### Music doesn't pause after timeout
- Check TimeoutCheckerFunction is running (EventBridge rule)
- Verify lastMotionTime is updating in DynamoDB

---

## Quick Reference Commands

**Check if sensor is registered:**
```bash
aws dynamodb get-item \
  --table-name spotty-potty-sense-SensorsTable-* \
  --key '{"sensorId":{"S":"bathroom-main"}}' \
  --region us-east-2
```

**List active sessions:**
```bash
aws dynamodb scan \
  --table-name spotty-potty-sense-SessionsTable-* \
  --filter-expression "#status = :s" \
  --expression-attribute-names '{"#status":"status"}' \
  --expression-attribute-values '{":s":{"S":"active"}}' \
  --region us-east-2
```

**Manually trigger Token Refresher:**
```bash
aws lambda invoke \
  --function-name spotty-potty-sense-TokenRefresherFunction-* \
  --region us-east-2 \
  /dev/stdout
```

---

## Success Checklist

- [ ] Spotify Developer App created
- [ ] Client credentials in AWS Secrets Manager
- [ ] OAuth tokens obtained (setup-spotify-oauth.sh)
- [ ] Cognito user created
- [ ] Spotify device ID identified
- [ ] Sensor registered with full configuration
- [ ] Motion triggers music playback ✨
- [ ] Timeout pauses music after 5 minutes

**You're all set! 🎉**
