# ESP8266 Quick Start Guide

Get your SpottyPottySense sensor running in 10 minutes!

## Prerequisites
- ✅ ESP8266 with PIR sensor connected
- ✅ Arduino IDE with ESP8266 support
- ✅ Backend deployed on AWS

---

## 1. Connect Hardware (2 min)

```
PIR Sensor → ESP8266
───────────────────
VCC → 3.3V or 5V
GND → GND  
OUT → D1
```

Adjust PIR: Sensitivity=medium, Delay=minimum, Mode=H

---

## 2. Get Certificates (3 min)

```bash
# Register device
aws lambda invoke \
  --function-name SpottyPottySense-DeviceRegistration-dev \
  --region us-east-2 \
  --payload '{"action":"register","sensorId":"bathroom-main","location":"Main Bathroom","userId":"YOUR_USER_ID"}' \
  response.json

# Extract
cat response.json | jq -r '.certificatePem' > device-cert.pem
cat response.json | jq -r '.privateKey' > private-key.pem
cat response.json | jq -r '.iotEndpoint'  # Save this!
```

---

## 3. Configure Firmware (2 min)

Edit `esp8266-sensor/config.h`:
```cpp
#define WIFI_SSID "YourWiFi"
#define WIFI_PASSWORD "YourPassword"
#define AWS_IOT_ENDPOINT "xxxxx-ats.iot.us-east-2.amazonaws.com"
#define SENSOR_ID "bathroom-main"
```

Edit `esp8266-sensor/certificates.h`:
- Paste content from `device-cert.pem` → `AWS_DEVICE_CERT`
- Paste content from `private-key.pem` → `AWS_PRIVATE_KEY`

---

## 4. Upload (3 min)

```
Arduino IDE:
1. File → Open → esp8266-sensor.ino
2. Tools → Board → NodeMCU 1.0
3. Tools → Port → Select your port
4. Click Upload (→)
5. Wait for "Done uploading"
```

---

## 5. Test! (Immediately)

Open Serial Monitor (115200 baud):
```
✓ Initialization complete!
✓ Ready to detect motion
```

Wave hand in front of PIR → Should see:
```
[Motion] ⚡ MOTION DETECTED!
[MQTT] ✓ Motion event published
```

LED flashes twice = Success! 🎉

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| WiFi fails | Check credentials, 2.4GHz network |
| MQTT fails | Verify certificates, IoT endpoint |
| No motion | Check PIR connections, power |
| Upload fails | Hold FLASH button, try again |

**Full guide:** See `docs/SETUP.md` and `docs/TROUBLESHOOTING.md`

---

## What's Next?

1. **Mount sensor** in final location
2. **Test range** - Verify detection distance
3. **Monitor CloudWatch** - Check backend processing
4. **Build dashboard** - View analytics (Phase 4)

**🎵 Enjoy automatic Spotify playback!**
