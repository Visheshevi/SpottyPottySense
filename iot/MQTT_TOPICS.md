# MQTT Topic Structure - SpottyPottySense

Complete documentation of all MQTT topics used in SpottyPottySense IoT system.

## Topic Naming Convention

```
sensors/{sensorId}/{action}
```

- `sensors/` - Root namespace for all sensor devices
- `{sensorId}` - Unique sensor identifier (e.g., `bathroom_main`, `bedroom_01`)
- `{action}` - Action type (motion, status, register, config, commands)

---

## Device → Cloud Topics (Publish)

Devices publish to these topics to send data to AWS IoT Core.

### 1. Motion Detection Topic

**Topic**: `sensors/{sensorId}/motion`

**Purpose**: Report motion detection events

**Publish Frequency**: On motion detected (debounced)

**Message Format**:
```json
{
  "event": "motion_detected",
  "sensorId": "bathroom_main",
  "timestamp": 1704412800,
  "metadata": {
    "batteryLevel": 85,
    "signalStrength": -45,
    "firmwareVersion": "1.0.0"
  }
}
```

**Fields**:
- `event` (string, required): Always "motion_detected"
- `sensorId` (string, required): Unique sensor ID
- `timestamp` (integer, required): Unix timestamp
- `metadata` (object, optional): Additional sensor information
  - `batteryLevel` (integer, optional): 0-100
  - `signalStrength` (integer, optional): dBm
  - `firmwareVersion` (string, optional): Firmware version

**IoT Rule**: Triggers `MotionHandlerFunction` Lambda

**Example ESP32 Code**:
```cpp
String topic = "sensors/" + sensorId + "/motion";
String payload = "{\"event\":\"motion_detected\",\"sensorId\":\"" + sensorId + "\",\"timestamp\":" + String(millis()) + "}";
client.publish(topic.c_str(), payload.c_str());
```

---

### 2. Status/Heartbeat Topic

**Topic**: `sensors/{sensorId}/status`

**Purpose**: Report device health and status

**Publish Frequency**: Every 5 minutes (configurable)

**Message Format**:
```json
{
  "event": "status",
  "sensorId": "bathroom_main",
  "timestamp": 1704412800,
  "status": "online",
  "uptime": 3600,
  "freeMemory": 120000,
  "wifiRssi": -45,
  "ipAddress": "192.168.1.100",
  "metadata": {
    "batteryLevel": 85,
    "batteryVoltage": 3.7,
    "temperature": 22.5
  }
}
```

**Fields**:
- `event` (string, required): Always "status"
- `status` (string, required): "online", "low_battery", "error"
- `uptime` (integer, optional): Seconds since boot
- `freeMemory` (integer, optional): Free RAM in bytes
- `wifiRssi` (integer, optional): WiFi signal strength (dBm)
- `ipAddress` (string, optional): Device IP address

**IoT Rule**: Optional - for monitoring/dashboards

---

### 3. Device Registration Topic

**Topic**: `sensors/{sensorId}/register`

**Purpose**: Register new device with backend

**Publish Frequency**: On first boot or after reset

**Message Format**:
```json
{
  "event": "registration",
  "sensorId": "bathroom_main",
  "timestamp": 1704412800,
  "deviceInfo": {
    "hardwareModel": "ESP32-WROOM-32",
    "firmwareVersion": "1.0.0",
    "macAddress": "AA:BB:CC:DD:EE:FF",
    "features": ["motion_detection", "battery_monitoring"]
  }
}
```

**Fields**:
- `event` (string, required): Always "registration"
- `deviceInfo` (object, required): Device specifications

**IoT Rule**: Triggers `DeviceRegistrationFunction` Lambda (optional - mainly for manual registration via API)

---

## Cloud → Device Topics (Subscribe)

Devices subscribe to these topics to receive commands from AWS IoT Core.

### 4. Configuration Updates Topic

**Topic**: `sensors/{sensorId}/config`

**Purpose**: Receive configuration updates from cloud

**Subscribe**: Device subscribes on connect

**Message Format**:
```json
{
  "action": "update_config",
  "timestamp": 1704412800,
  "config": {
    "motionDebounceSeconds": 120,
    "statusReportIntervalSeconds": 300,
    "sleepModeEnabled": false,
    "ledEnabled": true
  }
}
```

**Fields**:
- `action` (string, required): "update_config", "restart", "ota_update"
- `config` (object, optional): New configuration values

**Device Action**: Update local configuration, save to EEPROM/Flash

---

### 5. Control Commands Topic

**Topic**: `sensors/{sensorId}/commands`

**Purpose**: Receive control commands (restart, OTA, test)

**Subscribe**: Device subscribes on connect

**Message Format**:
```json
{
  "command": "restart",
  "timestamp": 1704412800,
  "parameters": {}
}
```

**Commands**:
- `restart` - Reboot device
- `test_motion` - Trigger test motion event
- `ota_update` - Start OTA firmware update
- `factory_reset` - Reset to factory defaults
- `enable` / `disable` - Enable/disable motion detection

**Device Action**: Execute command and publish result to status topic

---

## Topic Examples by Sensor

### Bathroom Main Sensor

```
sensors/bathroom_main/motion       ← Device publishes
sensors/bathroom_main/status       ← Device publishes
sensors/bathroom_main/register     ← Device publishes (once)
sensors/bathroom_main/config       → Device subscribes
sensors/bathroom_main/commands     → Device subscribes
```

### Bedroom Sensor

```
sensors/bedroom_01/motion
sensors/bedroom_01/status
sensors/bedroom_01/register
sensors/bedroom_01/config
sensors/bedroom_01/commands
```

---

## QoS (Quality of Service) Levels

| Topic Type | QoS | Reason |
|------------|-----|--------|
| motion | 1 | At least once delivery (important) |
| status | 0 | Best effort (periodic, can miss) |
| register | 1 | At least once delivery |
| config | 1 | At least once delivery |
| commands | 1 | At least once delivery |

**QoS Levels**:
- **QoS 0**: At most once (fire and forget)
- **QoS 1**: At least once (acknowledged)
- **QoS 2**: Exactly once (not supported by AWS IoT Core)

---

## Message Size Limits

- **Maximum payload size**: 128 KB per message
- **Recommended payload size**: < 4 KB for efficiency
- **Topic name length**: < 256 characters

---

## Security

### Authentication
- **Method**: X.509 certificate-based mutual TLS
- **Certificate**: Unique per device
- **Private Key**: Stored securely on device (never transmitted)

### Authorization
- **Method**: AWS IoT Policy attached to certificate
- **Scope**: Device can only publish/subscribe to own topics
- **Pattern**: Topics contain `${iot:Connection.Thing.ThingName}` variable

---

## Testing MQTT Topics

### Using AWS IoT Test Client (Console)

1. Go to AWS IoT Core → Test
2. Subscribe to topic: `sensors/+/motion`
3. Publish test message:

```json
{
  "event": "motion_detected",
  "sensorId": "test_sensor",
  "timestamp": 1704412800
}
```

### Using AWS CLI

**Subscribe (listen)**:
```bash
aws iot-data subscribe \
  --topic 'sensors/+/motion' \
  --query 'messages[*].[topic,payload]'
```

**Publish**:
```bash
aws iot-data publish \
  --topic sensors/test_sensor/motion \
  --payload '{"event":"motion_detected","sensorId":"test_sensor","timestamp":1704412800}' \
  --cli-binary-format raw-in-base64-out
```

### Using Mosquitto Client

**Subscribe**:
```bash
mosquitto_sub \
  -h YOUR_IOT_ENDPOINT.iot.us-east-1.amazonaws.com \
  -p 8883 \
  --cert device.pem.crt \
  --key private.pem.key \
  --cafile AmazonRootCA1.pem \
  -t 'sensors/+/motion' \
  -q 1
```

**Publish**:
```bash
mosquitto_pub \
  -h YOUR_IOT_ENDPOINT.iot.us-east-1.amazonaws.com \
  -p 8883 \
  --cert device.pem.crt \
  --key private.pem.key \
  --cafile AmazonRootCA1.pem \
  -t sensors/bathroom_main/motion \
  -m '{"event":"motion_detected","sensorId":"bathroom_main","timestamp":1704412800}' \
  -q 1
```

---

## Topic Patterns for IoT Rules

AWS IoT Rules use SQL-like syntax to filter messages:

### Motion Detection Rule
```sql
SELECT *, topic(2) as sensorId 
FROM 'sensors/+/motion'
WHERE event = 'motion_detected'
```

Explanation:
- `+` = Single-level wildcard (matches any sensorId)
- `topic(2)` = Extract 2nd segment from topic (sensorId)
- `WHERE` = Filter only motion_detected events

### All Sensor Events Rule
```sql
SELECT *, topic(2) as sensorId, topic(3) as action
FROM 'sensors/+/+'
```

Explanation:
- First `+` = Match any sensorId
- Second `+` = Match any action
- Captures all messages from all sensors

---

## Best Practices

### Device Side

1. **Use persistent sessions** for QoS 1
2. **Implement exponential backoff** for reconnection
3. **Buffer messages** when offline, send on reconnect
4. **Use clean sessions** = false for QoS 1 delivery
5. **Keep topic names short** for efficiency
6. **Use JSON** for message payload
7. **Include timestamp** in every message
8. **Implement local debouncing** before publishing

### Backend Side

1. **Use IoT Rules** for filtering and routing
2. **Set appropriate TTL** for retained messages
3. **Monitor CloudWatch metrics** for message rates
4. **Use Dead Letter Queues** for failed actions
5. **Log all IoT Rule errors**
6. **Implement message validation** in Lambda

---

## Troubleshooting

### Device Can't Publish

1. ✅ Check certificate is attached to Thing
2. ✅ Check IoT Policy allows publish to topic
3. ✅ Verify topic name matches pattern
4. ✅ Check device clock is synchronized (TLS requirement)
5. ✅ Verify certificate not expired
6. ✅ Check IoT endpoint URL is correct

### Messages Not Reaching Lambda

1. ✅ Check IoT Rule is enabled
2. ✅ Verify rule SQL syntax
3. ✅ Check CloudWatch Logs for rule errors
4. ✅ Verify Lambda has correct permissions
5. ✅ Check rule action configuration

### High Message Costs

1. ✅ Implement client-side debouncing
2. ✅ Reduce status heartbeat frequency
3. ✅ Use QoS 0 for non-critical messages
4. ✅ Batch multiple updates if possible

---

## Quick Reference

| Topic | Direction | QoS | Purpose |
|-------|-----------|-----|---------|
| `sensors/{id}/motion` | Device → Cloud | 1 | Motion events |
| `sensors/{id}/status` | Device → Cloud | 0 | Health status |
| `sensors/{id}/register` | Device → Cloud | 1 | Registration |
| `sensors/{id}/config` | Cloud → Device | 1 | Configuration |
| `sensors/{id}/commands` | Cloud → Device | 1 | Control commands |

---

## Related Documentation

- [AWS IoT Core Documentation](https://docs.aws.amazon.com/iot/)
- [MQTT Specification](https://mqtt.org/mqtt-specification/)
- [AWS IoT Device SDK](https://github.com/aws/aws-iot-device-sdk-embedded-C)
- [Mosquitto MQTT Client](https://mosquitto.org/man/mosquitto_pub-1.html)

---

**Last Updated**: January 4, 2026  
**Version**: 1.0.0  
**Maintained By**: SpottyPottySense Team

