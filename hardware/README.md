# SpottyPottySense ESP8266 Hardware

ESP8266-based motion sensor firmware for AWS IoT Core integration.

## Hardware Requirements

### Components
- **ESP8266** (NodeMCU, Wemos D1 Mini, or similar)
- **PIR Motion Sensor** (HC-SR501 or compatible)
- **Power Supply** (5V micro USB or 3.3V regulated)
- **Jumper Wires**

### Pin Connections

| Component | ESP8266 Pin | Notes |
|-----------|-------------|-------|
| PIR VCC | 3.3V or 5V | Check PIR voltage requirement |
| PIR GND | GND | Common ground |
| PIR OUT | D1 (GPIO5) | Digital input |
| LED (optional) | D4 (GPIO2) | Built-in LED (LOW = ON) |

### PIR Sensor Configuration
- **Sensitivity:** Adjust potentiometer for detection range (3-7 meters)
- **Time Delay:** Set to minimum (~3 seconds)
- **Trigger Mode:** Repeatable (H position on jumper)

## Software Requirements

### Arduino IDE Setup
1. **Install Arduino IDE** (v2.0+)
   ```bash
   # Download from: https://www.arduino.cc/en/software
   ```

2. **Add ESP8266 Board Support**
   - Open Arduino IDE → Preferences
   - Add to "Additional Boards Manager URLs":
     ```
     http://arduino.esp8266.com/stable/package_esp8266com_index.json
     ```
   - Tools → Board → Boards Manager → Search "ESP8266" → Install

3. **Install Required Libraries**
   - Sketch → Include Library → Manage Libraries
   - Install:
     - `PubSubClient` (v2.8.0+) - MQTT client
     - `ArduinoJson` (v6.21.0+) - JSON parsing
     - `WiFiManager` (optional, v2.0.16+) - WiFi config

### Required Files from AWS IoT
Before uploading firmware, you need certificates from device registration:

1. **Device Certificate** (`device-cert.pem`)
2. **Private Key** (`private-key.pem`)
3. **Root CA Certificate** (`root-ca.pem`)

Get these by running:
```bash
# Register device via API
aws lambda invoke \
  --function-name SpottyPottySense-DeviceRegistration-dev \
  --region us-east-2 \
  --payload '{"action":"register","sensorId":"bathroom-main","location":"Main Bathroom","userId":"your-user-id"}' \
  response.json

# Extract certificates
cat response.json | jq -r '.certificatePem' > device-cert.pem
cat response.json | jq -r '.privateKey' > private-key.pem

# Get Root CA
curl https://www.amazontrust.com/repository/AmazonRootCA1.pem -o root-ca.pem
```

## Project Structure

```
hardware/
├── README.md                    # This file
├── esp8266-sensor/             # Arduino project
│   ├── esp8266-sensor.ino      # Main firmware
│   ├── config.h                # Configuration
│   ├── certificates.h          # AWS IoT certificates
│   ├── wifi_manager.h          # WiFi connection
│   ├── aws_iot_client.h        # AWS IoT MQTT
│   └── motion_sensor.h         # Motion detection
├── data/                        # SPIFFS filesystem (optional)
│   ├── device-cert.pem
│   ├── private-key.pem
│   └── root-ca.pem
└── docs/
    ├── SETUP.md                 # Setup guide
    ├── TROUBLESHOOTING.md       # Common issues
    └── PINOUT.md                # Hardware connections
```

## Quick Start

### 1. Configure Firmware
Edit `esp8266-sensor/config.h`:
```cpp
// WiFi Configuration
#define WIFI_SSID "YourWiFiSSID"
#define WIFI_PASSWORD "YourWiFiPassword"

// AWS IoT Configuration
#define AWS_IOT_ENDPOINT "xxxxx.iot.us-east-2.amazonaws.com"
#define SENSOR_ID "bathroom-main"
#define MQTT_TOPIC_MOTION "sensors/bathroom-main/motion"
```

### 2. Add Certificates
Edit `esp8266-sensor/certificates.h`:
- Paste your device certificate, private key, and root CA

### 3. Upload Firmware
```bash
# Open Arduino IDE
# File → Open → esp8266-sensor/esp8266-sensor.ino

# Select board: Tools → Board → ESP8266 → NodeMCU 1.0
# Select port: Tools → Port → /dev/cu.usbserial-XXXX
# Upload: Sketch → Upload (Ctrl+U)
```

### 4. Monitor Serial Output
```bash
# Tools → Serial Monitor (115200 baud)
```

Expected output:
```
[WiFi] Connecting to YourWiFiSSID...
[WiFi] Connected! IP: 192.168.1.100
[AWS IoT] Connecting to AWS IoT Core...
[AWS IoT] Connected!
[Motion] Sensor initialized on pin D1
[Motion] Ready to detect motion
```

## Firmware Features

### Core Functionality
- ✅ WiFi auto-reconnect with exponential backoff
- ✅ AWS IoT Core MQTT over TLS 1.2
- ✅ X.509 certificate authentication
- ✅ Motion detection with debounce
- ✅ Publish to `sensors/{id}/motion` topic
- ✅ Status LED indicators
- ✅ Watchdog timer for stability
- ✅ OTA update support (future)

### Motion Detection Logic
1. **PIR triggers** → Read digital pin
2. **Debounce check** → Ignore events < 2 minutes apart
3. **Publish MQTT** → Send to AWS IoT Core
4. **LED feedback** → Flash on successful publish
5. **Log serial** → Debug output

### Error Handling
- WiFi disconnection → Auto-reconnect
- MQTT disconnection → Reconnect with backoff
- Certificate errors → Log and retry
- Sensor errors → Continue operation, log errors

## Configuration Options

### In `config.h`:
```cpp
// Network
#define WIFI_CONNECT_TIMEOUT 30000     // 30 seconds
#define MQTT_RECONNECT_DELAY 5000      // 5 seconds

// Motion Detection
#define PIR_PIN D1                     // GPIO5
#define DEBOUNCE_TIME 120000           // 2 minutes (120 seconds)
#define LED_PIN LED_BUILTIN            // GPIO2

// MQTT
#define MQTT_PORT 8883                 // TLS port
#define MQTT_BUFFER_SIZE 512           // Message buffer
#define MQTT_KEEPALIVE 60              // 60 seconds
```

## Power Consumption

### Normal Operation
- **Active (WiFi connected):** ~80mA @ 3.3V
- **Deep sleep (future):** ~20µA @ 3.3V
- **Transmitting:** ~170mA peak @ 3.3V

### Power Supply Recommendations
- USB power adapter: 5V/1A minimum
- Battery operation: 18650 Li-ion (3400mAh) = ~40 hours active
- With deep sleep: Several weeks on battery

## Troubleshooting

### WiFi Won't Connect
```cpp
// Check credentials in config.h
// Verify 2.4GHz WiFi (ESP8266 doesn't support 5GHz)
// Check signal strength: WiFi.RSSI() > -70
```

### MQTT Connection Fails
```cpp
// Verify AWS IoT endpoint is correct
// Check certificates are properly formatted
// Ensure IoT Policy allows iot:Connect
// Check NTP time sync (required for TLS)
```

### Motion Not Detected
```cpp
// Check PIR sensor power (3.3V or 5V)
// Verify pin connection (D1 = GPIO5)
// Adjust PIR sensitivity potentiometer
// Check sensor is in repeatable trigger mode
```

### Frequent Disconnections
```cpp
// Check power supply stability
// Verify WiFi signal strength
// Increase MQTT keepalive interval
// Add external antenna if needed
```

## Security Notes

### Certificate Storage
- ⚠️ **NEVER commit certificates to git**
- Use `.gitignore` for `certificates.h`
- Store certificates securely
- Rotate certificates periodically

### Network Security
- Use WPA2/WPA3 WiFi encryption
- Consider VPN for extra security
- Firewall rules: Allow outbound 8883/TCP
- Monitor AWS CloudWatch for anomalies

## Performance Optimization

### Memory Management
- ESP8266 has ~45KB free RAM
- Use `F()` macro for strings in PROGMEM
- Minimize global variables
- Reuse buffers where possible

### Power Optimization (Future)
```cpp
// Deep sleep between motion events
ESP.deepSleep(600e6); // 10 minutes

// Light sleep during idle
WiFi.setSleepMode(WIFI_LIGHT_SLEEP);
```

## Updates & Maintenance

### OTA Updates (Coming Soon)
- Upload firmware over WiFi
- No physical access required
- Rollback on failure
- Staged deployments

### Monitoring
- Check AWS IoT Core metrics
- Monitor DynamoDB for events
- CloudWatch logs for errors
- Battery voltage (if applicable)

## Related Documentation
- [AWS IoT Core Setup](../iot/README.md)
- [Backend Integration](../backend/README.md)
- [API Documentation](../PHASE_2.7_COMPLETE.md)

## Support
For issues:
1. Check serial monitor output
2. Review troubleshooting section
3. Check AWS IoT Core logs
4. Verify certificates and policies
