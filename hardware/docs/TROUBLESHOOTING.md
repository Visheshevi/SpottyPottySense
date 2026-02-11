# ESP8266 Troubleshooting Guide

Solutions to common issues with the SpottyPottySense ESP8266 firmware.

---

## WiFi Issues

### WiFi Won't Connect

**Symptoms:**
```
[WiFi] Connecting to: YourWiFi
..................
[WiFi] ✗ Connection failed!
[WiFi] Restarting in 5 seconds...
```

**Solutions:**

1. **Check WiFi Credentials**
   ```cpp
   // config.h - Verify these are correct
   #define WIFI_SSID "YourActualSSID"  // Case sensitive!
   #define WIFI_PASSWORD "YourPassword"
   ```

2. **Verify 2.4GHz Network**
   - ESP8266 only supports 2.4GHz WiFi
   - Does NOT work with 5GHz networks
   - Check router settings

3. **Check WiFi Signal**
   ```cpp
   // After connecting, check RSSI
   Serial.println(WiFi.RSSI());
   // Good: -30 to -67 dBm
   // Fair: -68 to -80 dBm  
   // Poor: < -80 dBm (won't work reliably)
   ```

4. **Router Configuration**
   - Disable MAC address filtering temporarily
   - Ensure DHCP is enabled
   - Try WPA2 (not WPA3 or WEP)

5. **Hidden SSID**
   - ESP8266 can connect to hidden SSIDs
   - Double-check spelling is exact

---

## AWS IoT Connection Issues

### MQTT Connection Fails

**Symptoms:**
```
[AWS IoT] Connecting to xxxxx.iot.us-east-2.amazonaws.com:8883
[AWS IoT] ✗ Connection failed, rc=-2
        MQTT_CONNECT_FAILED
```

**Common Error Codes:**

| Code | Meaning | Solution |
|------|---------|----------|
| -4 | MQTT_CONNECTION_TIMEOUT | Check IoT endpoint, network |
| -2 | MQTT_CONNECT_FAILED | Verify certificates, time sync |
| 2 | MQTT_CONNECT_BAD_CLIENT_ID | Check SENSOR_ID format |
| 4 | MQTT_CONNECT_BAD_CREDENTIALS | Fix certificates |
| 5 | MQTT_CONNECT_UNAUTHORIZED | Check IoT Policy |

### Solution 1: Verify IoT Endpoint

```bash
# Get correct endpoint
aws iot describe-endpoint \
  --endpoint-type iot:Data-ATS \
  --region us-east-2

# Should return something like:
# "xxxxx-ats.iot.us-east-2.amazonaws.com"
```

Update in `config.h`:
```cpp
#define AWS_IOT_ENDPOINT "xxxxx-ats.iot.us-east-2.amazonaws.com"
```

### Solution 2: Check Certificates

**Certificate Format Issues:**

❌ **Wrong:**
```cpp
const char AWS_DEVICE_CERT[] = "-----BEGIN CERTIFICATE-----\nMIIDWj...";
```

✅ **Correct:**
```cpp
const char AWS_DEVICE_CERT[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDWjCCAkKgAwIBAgIVAK...
(full certificate here)
...
-----END CERTIFICATE-----
)EOF";
```

**Verify Certificate Length:**
- Device cert: ~1200-1500 characters
- Private key: ~1600-1700 characters
- If shorter, certificate is incomplete

**Re-extract Certificates:**
```bash
# From registration response
cat response.json | jq -r '.certificatePem' > device-cert.pem
cat response.json | jq -r '.privateKey' > private-key.pem

# Verify files are not empty
wc -l device-cert.pem private-key.pem
```

### Solution 3: NTP Time Sync

TLS requires accurate time. If time sync fails:

```
[NTP] Syncing time......................
[NTP] ✗ Time sync failed!
```

**Fixes:**
1. Check internet connectivity
2. Try different NTP servers in firmware:
   ```cpp
   configTime(0, 0, "time.google.com", "pool.ntp.org");
   ```
3. Increase timeout:
   ```cpp
   #define NTP_MAX_RETRIES 60  // Increase from 30
   ```

### Solution 4: IoT Policy

Verify your IoT Policy allows connection:

```bash
# Check policy
aws iot get-policy \
  --policy-name SpottyPottySense-SensorPolicy \
  --region us-east-2
```

Required permissions:
```json
{
  "Effect": "Allow",
  "Action": [
    "iot:Connect",
    "iot:Publish",
    "iot:Subscribe",
    "iot:Receive"
  ],
  "Resource": "*"
}
```

### Solution 5: Certificate Status

Check if certificate is active:

```bash
# Get certificate ID from response.json
CERT_ID=$(cat response.json | jq -r '.certificateId')

# Check certificate status
aws iot describe-certificate \
  --certificate-id $CERT_ID \
  --region us-east-2
```

Status should be "ACTIVE". If not:
```bash
# Activate certificate
aws iot update-certificate \
  --certificate-id $CERT_ID \
  --new-status ACTIVE \
  --region us-east-2
```

---

## Motion Detection Issues

### Motion Not Detected

**Symptoms:**
- No serial output when moving
- LED doesn't flash
- No MQTT messages published

**Solutions:**

1. **Check Pin Connection**
   ```
   PIR OUT → ESP8266 D1 (GPIO5)
   ```
   Verify with multimeter: PIR OUT should be HIGH (3.3V) when triggered

2. **Test PIR Sensor**
   ```cpp
   // Add to loop() temporarily
   Serial.print("PIR State: ");
   Serial.println(digitalRead(PIR_PIN));
   delay(1000);
   ```
   Should print `1` when motion detected, `0` otherwise

3. **Check PIR Power**
   - Verify VCC connected to 3.3V or 5V (check PIR specs)
   - Ensure GND connected
   - PIR LED should light when powered

4. **Adjust PIR Sensitivity**
   - Turn Sx potentiometer clockwise (increase range)
   - Turn Tx potentiometer fully counter-clockwise (minimum delay)
   - Set jumper to H position (repeatable trigger)

5. **PIR Warm-up Time**
   - PIR sensors need 30-60 seconds to stabilize after power-on
   - Wait before testing

### Motion Detected But Not Published

**Symptoms:**
```
[Motion] ⚡ MOTION DETECTED!
[MQTT] ✗ Failed to publish motion event
```

**Solutions:**

1. **Check MQTT Connection**
   ```cpp
   if (!mqttClient.connected()) {
     Serial.println("MQTT not connected!");
   }
   ```

2. **Increase Buffer Size**
   ```cpp
   // config.h
   #define MQTT_BUFFER_SIZE 1024  // Increase from 512
   ```

3. **Check Topic Format**
   ```cpp
   // Should be: sensors/{SENSOR_ID}/motion
   // Verify SENSOR_ID is set correctly in config.h
   ```

### Rapid Re-triggering

**Symptoms:**
- Motion events every few seconds
- Debounce not working

**Solution:**
Adjust debounce time in `config.h`:
```cpp
#define DEBOUNCE_TIME 180000  // 3 minutes instead of 2
```

---

## Memory Issues

### Out of Memory / Crashes

**Symptoms:**
```
Fatal exception (9):
epc1=0x40100001, epc2=0x00000000, epc3=0x00000000, excvaddr=0x00000000
```

**Solutions:**

1. **Check Free Heap**
   ```cpp
   Serial.print("Free heap: ");
   Serial.println(ESP.getFreeHeap());
   // Should be > 8192 bytes
   ```

2. **Reduce Buffer Sizes**
   ```cpp
   // config.h
   #define MQTT_BUFFER_SIZE 256  // Reduce from 512
   ```

3. **Use PROGMEM for Strings**
   ```cpp
   Serial.println(F("This string in flash memory"));
   ```

4. **Flash Size Settings**
   - Tools → Flash Size → 4MB (FS:1MB OTA:~1019KB)
   - More RAM available with smaller FS

---

## Power Issues

### Frequent Reboots

**Symptoms:**
```
ets Jan  8 2013,rst cause:2, boot mode:(3,6)
```

**Solutions:**

1. **Check Power Supply**
   - Use quality USB power adapter (5V/1A minimum)
   - Avoid USB hubs
   - Try different USB cable

2. **Add Capacitor**
   - 100µF capacitor between 3.3V and GND
   - Reduces voltage spikes

3. **Reduce WiFi Power**
   ```cpp
   // After WiFi.begin()
   WiFi.setOutputPower(15);  // Reduce from 20.5dBm
   ```

### Brown-out Detector

**Symptoms:**
```
Brownout detector was triggered
```

**Solutions:**
- Use external 3.3V regulator (AMS1117, LD1117)
- Powered from 5V USB with proper regulator
- Check power supply capacity (min 500mA)

---

## Upload Issues

### Upload Fails

**Symptoms:**
```
Connecting...
...._____....._____...
```

**Solutions:**

1. **Hold FLASH Button**
   - Hold FLASH/BOOT button on ESP8266
   - Click Upload in Arduino IDE
   - Release button after "Uploading..." appears

2. **Check USB Driver**
   - NodeMCU: CH340 driver
   - Wemos D1 Mini: CH340 driver
   - Download from: http://www.wch.cn/downloads/CH341SER_ZIP.html

3. **Try Different Upload Speed**
   - Tools → Upload Speed → 115200 (try slower)

4. **Reset Board**
   - Press RST button
   - Try upload again

5. **Check USB Cable**
   - Use data cable (not charge-only)
   - Try different cable/port

---

## Debugging Tips

### Enable Verbose Logging

1. **Arduino IDE:**
   - Tools → Core Debug Level → Verbose
   - More detailed output

2. **Firmware Debug:**
   ```cpp
   // config.h
   #define DEBUG_ENABLED true
   
   // Use in code
   DEBUG_PRINTLN("Debug message");
   ```

### Monitor MQTT Traffic

```bash
# Subscribe to all sensor topics
aws iot-data subscribe \
  --topic 'sensors/+/motion' \
  --region us-east-2

# Or use MQTT.fx / MQTT Explorer tools
```

### Check AWS CloudWatch

```bash
# Motion handler logs
aws logs tail /aws/lambda/SpottyPottySense-MotionHandler-dev \
  --region us-east-2 \
  --follow

# Check for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/SpottyPottySense-MotionHandler-dev \
  --filter-pattern "ERROR" \
  --region us-east-2
```

### Test MQTT Locally

Use MQTT test client to verify endpoint:
```bash
# Install mosquitto
brew install mosquitto  # macOS
# or: apt-get install mosquitto-clients  # Linux

# Test connection (won't work without certs, but tests endpoint)
mosquitto_pub -h xxxxx-ats.iot.us-east-2.amazonaws.com \
  -p 8883 \
  -t 'test/topic' \
  -m 'test' \
  --cafile root-ca.pem \
  --cert device-cert.pem \
  --key private-key.pem
```

---

## Performance Issues

### Slow Response

**Solutions:**

1. **Improve WiFi Signal**
   - Move closer to router
   - Use external antenna
   - Reduce interference

2. **Optimize Code**
   ```cpp
   // Reduce keepalive
   #define MQTT_KEEPALIVE 30  // From 60
   
   // Faster WiFi connection
   WiFi.setAutoReconnect(true);
   ```

3. **Increase CPU Frequency**
   - Tools → CPU Frequency → 160 MHz

### High Latency

Check end-to-end latency:
```cpp
// In motion event payload
doc["deviceTimestamp"] = millis();

// Compare with backend timestamp in CloudWatch
```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `rst cause:2` | Watchdog reset | Power issue or infinite loop |
| `rst cause:4` | Hardware watchdog | Software crash, check code |
| `Exception (28)` | Stack overflow | Reduce recursion, local vars |
| `Exception (9)` | Invalid memory access | Null pointer, bad array index |
| `wdt reset` | Watchdog timeout | Blocking code, add yield() |
| `load 0x4010f000` | Normal boot | Not an error |

---

## Getting More Help

### Serial Monitor Output

When reporting issues, include:
1. Full serial monitor output from boot
2. Error messages and codes
3. Hardware configuration
4. Firmware version

### Check System Status

```cpp
// Add to setup() or loop()
Serial.printf("Chip ID: %08X\n", ESP.getChipId());
Serial.printf("Flash ID: %08X\n", ESP.getFlashChipId());
Serial.printf("Flash Size: %d\n", ESP.getFlashChipRealSize());
Serial.printf("Free Heap: %d\n", ESP.getFreeHeap());
Serial.printf("SDK Version: %s\n", ESP.getSdkVersion());
```

### Community Resources

- ESP8266 Arduino Core: https://github.com/esp8266/Arduino
- ESP8266 Community Forum: https://www.esp8266.com/
- AWS IoT Documentation: https://docs.aws.amazon.com/iot/
- PubSubClient Issues: https://github.com/knolleary/pubsubclient

---

## Still Having Issues?

1. **Check AWS IoT Core logs** in CloudWatch
2. **Verify backend is deployed** and working
3. **Test with integration tests** to isolate issue
4. **Review setup guide** step by step
5. **Check DynamoDB** for sensor registration

**Remember:** Most issues are certificate or configuration related!
