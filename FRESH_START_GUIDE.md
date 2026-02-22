# 🚀 Fresh Start Setup Guide

Complete clean setup for SpottyPottySense from scratch.

---

## ✅ Cleanup Complete

All previous registrations have been removed:
- ✓ IoT Things deleted
- ✓ Certificates deleted
- ✓ DynamoDB records cleared

---

## 📋 Complete Setup in 4 Steps

### Step 1: Provision New Sensor (5 min)

Choose a sensor ID and provision it:

```bash
./scripts/provision-esp8266.sh bathroom-main "Main Bathroom" "spotify:22ouf7ogdosi54aixkiitc7gy"
```

**Replace with your info:**
- `bathroom-main` → Your chosen sensor ID (letters, numbers, hyphens only)
- `"Main Bathroom"` → Location description
- `"spotify:..."` → Your Spotify user ID (from OAuth setup)

**Output:**
```
✓ Device registered successfully
✓ Certificates extracted
✓ certificates.h generated
```

### Step 2: Update ESP8266 Config (1 min)

Your `config.local.h` should match the sensor ID you just provisioned.

**Check line 24:**
```cpp
#define SENSOR_ID "bathroom-main"  // Must match what you provisioned!
```

If it's different, update it to match.

### Step 3: Upload Firmware (2 min)

**In Arduino IDE:**
1. Open `hardware/esp8266-sensor/esp8266-sensor.ino`
2. Click **Verify** (✓)
   - Look for: `✓ Using config.local.h for credentials`
3. Click **Upload** (→)
4. Open **Serial Monitor** (115200 baud)

**Wait for:**
```
[MQTT] ✓ Connected!
✓ Ready to detect motion
```

### Step 4: Register with Spotify Config (3 min)

```bash
./scripts/register-sensor.sh
```

**Enter:**
- **Sensor ID**: `bathroom-main` (same as provisioned!)
- **Location**: `Main Bathroom`
- **User ID**: `spotify:22ouf7ogdosi54aixkiitc7gy`
- **Spotify Device ID**: (paste from list-devices script)
- **Playlist**: Press Enter for default
- **Timeout**: `5`
- **Debounce**: `2`

**Confirm:** Type `y` and press Enter

---

## 🎉 Test It!

**Trigger motion** → Watch 3 places:

**1. Serial Monitor (ESP8266):**
```
[MOTION] Detected! Publishing event...
[MQTT] ✓ Motion event published
```

**2. Lambda Logs:**
```bash
aws logs tail /aws/lambda/SpottyPottySense-MotionHandler-dev --follow --region us-east-2
```

Should show:
```
[INFO] Motion event received from sensor: bathroom-main
[INFO] Starting Spotify playback
[INFO] ✓ Playback started successfully
```

**3. Spotify App:**
- **Music should start playing!** 🎶

---

## 🔍 Troubleshooting Checklist

Before testing, verify:

- [ ] **Sensor ID matches** everywhere:
  - `config.local.h` → `SENSOR_ID`
  - `register-sensor.sh` → Sensor ID input
  - Both should be identical!

- [ ] **ESP8266 shows**:
  - `[MQTT] ✓ Connected!`
  - If disconnected, check certificates.h was generated

- [ ] **Spotify setup complete**:
  - User exists in DynamoDB (Users table)
  - Tokens in Secrets Manager
  - Device ID is valid

- [ ] **Registration has all fields**:
  ```bash
  aws dynamodb get-item \
    --table-name SpottyPottySense-Sensors-dev \
    --key '{"sensorId":{"S":"bathroom-main"}}' \
    --region us-east-2
  ```
  Should show: userId, spotifyDeviceId, playlistUri, timeoutMinutes

---

## Quick Reference Commands

**Check if sensor exists:**
```bash
aws dynamodb get-item \
  --table-name SpottyPottySense-Sensors-dev \
  --key '{"sensorId":{"S":"YOUR_SENSOR_ID"}}' \
  --region us-east-2 | python3 -m json.tool
```

**Check IoT connection:**
```bash
aws iot describe-thing --thing-name SpottyPottySense-YOUR_SENSOR_ID --region us-east-2
```

**Monitor motion events:**
```bash
aws dynamodb scan \
  --table-name SpottyPottySense-MotionEvents-dev \
  --region us-east-2 \
  --limit 5
```

**Watch Lambda logs:**
```bash
aws logs tail /aws/lambda/SpottyPottySense-MotionHandler-dev --follow --region us-east-2
```

---

## 📝 Summary

**You're starting with:**
- ✓ Clean AWS IoT (no Things)
- ✓ Clean Sensors table (no records)
- ✓ Your Spotify OAuth tokens still saved
- ✓ Your certificates.h cleared (will regenerate)

**Follow the 4 steps above in order for a successful setup!**
