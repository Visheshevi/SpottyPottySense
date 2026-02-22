# 🚀 5-Minute Spotify Setup

Get SpottyPottySense working with Spotify in 5 simple commands.

---

## Prerequisites

- ✅ AWS backend deployed
- ✅ ESP8266 connected to AWS IoT
- 🎵 Spotify Premium account

---

## Setup Commands (Run in Order)

### 1️⃣ Create Spotify App
Visit: https://developer.spotify.com/dashboard
- Create app named "SpottyPottySense"
- Redirect URI: `http://127.0.0.1:8888/callback`
- Copy Client ID and Secret

### 2️⃣ Store Client Credentials
```bash
aws secretsmanager create-secret \
  --name "spotty-potty-sense/spotify/client" \
  --secret-string '{"client_id":"YOUR_ID","client_secret":"YOUR_SECRET"}' \
  --region us-east-2
```

### 3️⃣ Authenticate & Get Tokens
```bash
./scripts/setup-spotify-oauth.sh
```
Saves your **User ID** - write it down!

### 4️⃣ Find Your Speaker
```bash
./scripts/list-spotify-devices.sh
```
Pick your bathroom speaker, copies **Device ID** to clipboard.

### 5️⃣ Register Sensor
```bash
./scripts/register-sensor.sh
```
Paste User ID and Device ID when prompted.

---

## Test It! 🎉

**Trigger motion** → Spotify plays in 2 seconds!

Watch it work:
```bash
# Terminal 1: Lambda logs
aws logs tail /aws/lambda/spotty-potty-sense-MotionHandlerFunction --follow --region us-east-2

# Terminal 2: Trigger motion on ESP8266
# Wave hand → Music starts! 🎶
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No devices found | Open Spotify app on your speaker/computer |
| 401 error in logs | Re-run `setup-spotify-oauth.sh` |
| Wrong device plays | Re-run `register-sensor.sh` with correct device ID |
| No Premium account | Upgrade to Spotify Premium (required for API control) |

---

**Need help?** See full guide: `SPOTIFY_INTEGRATION_GUIDE.md`
