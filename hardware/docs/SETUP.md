# ESP8266 Setup Guide

Complete step-by-step guide to set up your SpottyPottySense ESP8266 motion sensor.

## Prerequisites

### Hardware
- ✅ ESP8266 module (NodeMCU, Wemos D1 Mini, or compatible)
- ✅ PIR Motion Sensor (HC-SR501 or similar)
- ✅ USB cable (micro USB)
- ✅ Jumper wires
- ✅ Breadboard (optional)

### Software
- ✅ Arduino IDE installed
- ✅ AWS account with IoT Core access
- ✅ SpottyPottySense backend deployed
- ✅ WiFi network (2.4GHz)

---

## Step 1: Hardware Assembly

### 1.1 PIR Sensor Connections

```
PIR Sensor    →    ESP8266
─────────────────────────────
VCC           →    3.3V or 5V
GND           →    GND
OUT           →    D1 (GPIO5)
```

### 1.2 PIR Sensor Configuration

**Adjust potentiometers on PIR sensor:**

1. **Sensitivity (Sx)** - Detection range
   - Turn clockwise: Increase range (up to 7 meters)
   - Turn counter-clockwise: Decrease range (down to 3 meters)
   - **Recommended:** Middle position (~5 meters)

2. **Time Delay (Tx)** - Output duration
   - Turn fully counter-clockwise: Minimum (~3 seconds)
   - **Recommended:** Minimum (we handle debounce in software)

3. **Trigger Mode** - Jumper setting
   - **H position:** Repeatable trigger (RECOMMENDED)
   - **L position:** Single trigger
   - Set to **H** for continuous detection

### 1.3 Connection Diagram

```
┌─────────────────────┐
│    PIR Sensor       │
│  ┌───────────────┐  │
│  │   HC-SR501    │  │
│  │  ┌─┐  ┌─┐    │  │
│  │  │S│  │T│ OUT├──┼──────┐
│  │  │x│  │x│    │  │      │
│  │  └─┘  └─┘    │  │      │
│  │   VCC  GND   │  │      │
│  └────┬────┬────┘  │      │
└───────┼────┼────────┘      │
        │    │                │
        │    │                │
┌───────┴────┴────────────────┴───┐
│         ESP8266 (NodeMCU)       │
│                                  │
│  3.3V  GND          D1          │
│  (or 5V)           GPIO5        │
│                                  │
│         USB Port                 │
└──────────────────────────────────┘
```

---

## Step 2: Arduino IDE Setup

### 2.1 Install Arduino IDE

1. Download from: https://www.arduino.cc/en/software
2. Install for your operating system
3. Launch Arduino IDE

### 2.2 Add ESP8266 Board Support

1. **Open Preferences**
   - File → Preferences (or Arduino → Preferences on macOS)

2. **Add Board Manager URL**
   - Find "Additional Boards Manager URLs"
   - Paste: `http://arduino.esp8266.com/stable/package_esp8266com_index.json`
   - Click OK

3. **Install ESP8266 Package**
   - Tools → Board → Boards Manager
   - Search for "esp8266"
   - Install "esp8266 by ESP8266 Community"
   - Wait for installation to complete

### 2.3 Install Required Libraries

1. **Open Library Manager**
   - Sketch → Include Library → Manage Libraries

2. **Install these libraries:**
   
   **PubSubClient** (MQTT client)
   - Search: "PubSubClient"
   - Install: "PubSubClient by Nick O'Leary"
   - Version: 2.8.0 or higher
   
   **ArduinoJson** (JSON parsing)
   - Search: "ArduinoJson"
   - Install: "ArduinoJson by Benoit Blanchon"
   - Version: 6.21.0 or higher
   - ⚠️ Use version 6.x, NOT 7.x

### 2.4 Select Board and Port

1. **Select Board**
   - Tools → Board → ESP8266 Boards → NodeMCU 1.0 (ESP-12E Module)
   - Or select your specific ESP8266 board

2. **Select Port**
   - Connect ESP8266 via USB
   - Tools → Port → Select your port
     - macOS: `/dev/cu.usbserial-XXXX` or `/dev/cu.wchusbserial-XXXX`
     - Windows: `COM3`, `COM4`, etc.
     - Linux: `/dev/ttyUSB0` or `/dev/ttyACM0`

3. **Configure Settings**
   - Tools → Upload Speed → 115200
   - Tools → CPU Frequency → 80 MHz
   - Tools → Flash Size → 4MB (FS:2MB OTA:~1019KB)

---

## Step 3: Get AWS IoT Credentials

### 3.1 Register Device

Run the device registration API:

```bash
# Set your parameters
SENSOR_ID="bathroom-main"
USER_ID="your-cognito-user-id"
LOCATION="Main Bathroom"

# Register device
aws lambda invoke \
  --function-name SpottyPottySense-DeviceRegistration-dev \
  --region us-east-2 \
  --cli-binary-format raw-in-base64-out \
  --payload "{\"action\":\"register\",\"sensorId\":\"$SENSOR_ID\",\"location\":\"$LOCATION\",\"userId\":\"$USER_ID\"}" \
  response.json

# View response
cat response.json | jq '.'
```

### 3.2 Extract Certificates

```bash
# Extract device certificate
cat response.json | jq -r '.certificatePem' > device-cert.pem

# Extract private key
cat response.json | jq -r '.privateKey' > private-key.pem

# Extract IoT endpoint
IOT_ENDPOINT=$(cat response.json | jq -r '.iotEndpoint')
echo "IoT Endpoint: $IOT_ENDPOINT"
```

### 3.3 Download Root CA

```bash
# Download Amazon Root CA 1
curl https://www.amazontrust.com/repository/AmazonRootCA1.pem -o root-ca.pem
```

---

## Step 4: Configure Firmware

### 4.1 Open Firmware

1. Navigate to firmware directory:
   ```bash
   cd hardware/esp8266-sensor/
   ```

2. Open in Arduino IDE:
   - File → Open → `esp8266-sensor.ino`

### 4.2 Update config.h

Open `config.h` and update:

```cpp
// WiFi Settings
#define WIFI_SSID "YourWiFiName"
#define WIFI_PASSWORD "YourWiFiPassword"

// AWS IoT Settings
#define AWS_IOT_ENDPOINT "xxxxx-ats.iot.us-east-2.amazonaws.com"
#define SENSOR_ID "bathroom-main"

// Motion Settings (optional)
#define DEBOUNCE_TIME 120000  // 2 minutes
```

**Get IoT Endpoint:**
```bash
# From registration response
cat response.json | jq -r '.iotEndpoint'

# Or from AWS CLI
aws iot describe-endpoint --endpoint-type iot:Data-ATS --region us-east-2
```

### 4.3 Update certificates.h

Open `certificates.h` and paste your certificates:

1. **Device Certificate** (AWS_DEVICE_CERT)
   ```bash
   cat device-cert.pem
   ```
   - Copy entire content including `-----BEGIN/END CERTIFICATE-----`
   - Paste into `AWS_DEVICE_CERT` section

2. **Private Key** (AWS_PRIVATE_KEY)
   ```bash
   cat private-key.pem
   ```
   - Copy entire content including `-----BEGIN/END RSA PRIVATE KEY-----`
   - Paste into `AWS_PRIVATE_KEY` section

3. **Root CA** (already included, no changes needed)

**⚠️ Security:**
```bash
# Add certificates.h to gitignore
echo "hardware/esp8266-sensor/certificates.h" >> .gitignore
```

---

## Step 5: Upload Firmware

### 5.1 Compile

1. Click **Verify** button (✓) or Sketch → Verify/Compile
2. Wait for compilation to complete
3. Check for errors in output window

**Expected output:**
```
Sketch uses 345678 bytes (33%) of program storage space.
Global variables use 28456 bytes (34%) of dynamic memory.
```

### 5.2 Upload

1. Connect ESP8266 via USB
2. Click **Upload** button (→) or Sketch → Upload
3. Wait for upload to complete (~30 seconds)

**Expected output:**
```
Uploading...
Writing at 0x00000000... (100%)
Wrote 345678 bytes in 25.3 seconds
Hard resetting via RTS pin...
```

### 5.3 Monitor Serial Output

1. Open Serial Monitor:
   - Tools → Serial Monitor
   - Or click magnifying glass icon

2. Set baud rate: **115200**

3. You should see:
```
╔════════════════════════════════════════════════════════╗
║      SpottyPottySense ESP8266 Motion Sensor v1.0      ║
╚════════════════════════════════════════════════════════╝

[GPIO] Motion sensor pin: D1 (GPIO5)
[GPIO] LED pin: D4 (GPIO2)
[WiFi] Connecting to: YourWiFiName
[WiFi] ✓ Connected!
[WiFi] IP Address: 192.168.1.100
[WiFi] Signal Strength: -45 dBm
[NTP] Syncing time...
[NTP] ✓ Time synced: Sat Feb  9 01:23:45 2026
[TLS] Configuring certificates...
[TLS] ✓ Certificates configured
[AWS IoT] Connecting to xxxxx-ats.iot.us-east-2.amazonaws.com:8883
[AWS IoT] ✓ Connected!
[MQTT] Subscribed to: sensors/bathroom-main/config
[Status] Published: online

✓ Initialization complete!
✓ Ready to detect motion
```

---

## Step 6: Test Motion Detection

### 6.1 Trigger Motion Sensor

1. Wave your hand in front of PIR sensor
2. Watch serial monitor for output
3. LED should flash twice

**Expected output:**
```
═══════════════════════════════════════════════════════
[Motion] ⚡ MOTION DETECTED!
═══════════════════════════════════════════════════════
[MQTT] ✓ Motion event published
[MQTT] Topic: sensors/bathroom-main/motion
[MQTT] Payload: {"sensorId":"bathroom-main","event":"motion_detected","timestamp":"2026-02-09T01:25:30Z","rssi":-45,"metadata":{"firmware":"1.0.0","uptime":105,"freeHeap":35432}}
```

### 6.2 Verify in AWS

**Check IoT Core:**
```bash
# Subscribe to motion topic
aws iot-data publish \
  --topic 'sensors/bathroom-main/motion' \
  --region us-east-2

# View CloudWatch logs
aws logs tail /aws/lambda/SpottyPottySense-MotionHandler-dev \
  --region us-east-2 \
  --follow
```

**Check DynamoDB:**
```bash
# Query sessions table
aws dynamodb query \
  --table-name SpottyPottySense-Sessions-dev \
  --index-name SensorIdIndex \
  --key-condition-expression "sensorId = :sid" \
  --expression-attribute-values '{":sid":{"S":"bathroom-main"}}' \
  --region us-east-2
```

---

## Step 7: Final Verification

### Checklist

- ✅ ESP8266 powers on and connects to WiFi
- ✅ Time syncs successfully (required for TLS)
- ✅ Connects to AWS IoT Core
- ✅ Motion events publish to MQTT
- ✅ Backend processes events (check CloudWatch)
- ✅ Sessions created in DynamoDB
- ✅ LED flashes on motion detection
- ✅ No errors in serial monitor

### Health Check Commands

```bash
# Check sensor status in DynamoDB
aws dynamodb get-item \
  --table-name SpottyPottySense-Sensors-dev \
  --key '{"sensorId":{"S":"bathroom-main"}}' \
  --region us-east-2

# Check IoT Thing
aws iot describe-thing \
  --thing-name SpottyPottySense-bathroom-main \
  --region us-east-2

# Check recent sessions
aws dynamodb query \
  --table-name SpottyPottySense-Sessions-dev \
  --index-name SensorIdIndex \
  --key-condition-expression "sensorId = :sid" \
  --expression-attribute-values '{":sid":{"S":"bathroom-main"}}' \
  --limit 5 \
  --scan-index-forward false \
  --region us-east-2
```

---

## Next Steps

1. **Mount Hardware** - Install in final location
2. **Test Range** - Verify PIR detection distance
3. **Adjust Debounce** - Tune `DEBOUNCE_TIME` if needed
4. **Monitor Performance** - Check AWS CloudWatch metrics
5. **Setup Dashboard** - Build frontend to view analytics

---

## Troubleshooting

If something doesn't work, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

Common issues:
- WiFi won't connect → Check SSID/password, 2.4GHz network
- MQTT fails → Verify certificates, IoT endpoint, NTP time
- Motion not detected → Check pin connections, PIR power
- Frequent disconnects → Check power supply, WiFi signal

---

## Support

- **Hardware Issues:** Check pin connections and power supply
- **Software Issues:** Review serial monitor output
- **AWS Issues:** Check CloudWatch logs and IoT Core metrics
- **Integration:** See [main README](../README.md)
