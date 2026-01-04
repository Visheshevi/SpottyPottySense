# AWS IoT Core Configuration

AWS IoT policies and rules for SpottyPottySense devices.

## Directory Structure

```
iot/
├── policies/              # IoT device policies (JSON)
│   └── sensor-policy.json
├── rules/                 # IoT Rule Engine SQL
│   ├── motion-detection-rule.sql
│   └── device-registration-rule.sql
└── README.md
```

## Overview

### IoT Things

Each sensor is registered as an IoT Thing:
- **Thing Name**: `sensor-{sensorId}` (e.g., `sensor-bathroom-main`)
- **Thing Type**: `SpottyPottySensor`
- **Certificate**: X.509 certificate for authentication

### MQTT Topics

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `sensors/{sensorId}/motion` | Device → Cloud | Motion detected event |
| `sensors/{sensorId}/status` | Device → Cloud | Device health/heartbeat |
| `sensors/{sensorId}/register` | Device → Cloud | Device registration |
| `sensors/{sensorId}/config` | Cloud → Device | Configuration updates |
| `sensors/{sensorId}/commands` | Cloud → Device | Control commands |

### Message Formats

**Motion Event:**
```json
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

**Status Update:**
```json
{
  "event": "status",
  "sensorId": "bathroom_main",
  "timestamp": 1704412800,
  "status": "online",
  "uptime": 3600,
  "freeMemory": 120000
}
```

## Policies

Device policies are defined in `policies/sensor-policy.json`.

### Permissions

Devices can:
- ✅ Connect to IoT Core
- ✅ Publish to their own sensor topics
- ✅ Subscribe to their own config/command topics
- ❌ Cannot access other devices' topics
- ❌ Cannot publish to system topics

### Policy Template

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
      "Resource": [
        "arn:aws:iot:REGION:ACCOUNT:topic/sensors/*/motion",
        "arn:aws:iot:REGION:ACCOUNT:topic/sensors/*/status"
      ]
    }
  ]
}
```

## Rules

IoT Rules route messages to Lambda functions.

### Rule 1: Motion Detection

**SQL:**
```sql
SELECT *, topic(2) as sensorId 
FROM 'sensors/+/motion'
WHERE event = 'motion_detected'
```

**Action:** Invoke `MotionHandlerFunction`

### Rule 2: Device Registration

**SQL:**
```sql
SELECT * 
FROM 'sensors/+/register'
```

**Action:** Invoke `DeviceRegistrationFunction`

## Security

1. **Certificate-based Authentication**
   - Each device has unique X.509 certificate
   - Private key stored only on device
   - Certificate rotated annually

2. **Policy-based Authorization**
   - Least privilege access
   - Device can only access its own topics
   - Enforced by IoT Core

3. **Encryption**
   - All traffic uses TLS 1.2+
   - Certificates signed by AWS IoT CA
   - No plaintext communication

## Device Provisioning

See `scripts/provision-device.sh` for automated provisioning:

1. Generate certificate via API
2. Create IoT Thing
3. Attach policy to certificate
4. Return certificate to user (one-time)
5. Device stores certificate in secure storage

## Testing

### Test MQTT Publishing

```bash
# Publish test message
aws iot-data publish \
  --topic sensors/test/motion \
  --payload '{"event":"motion_detected","sensorId":"test","timestamp":1704412800}' \
  --cli-binary-format raw-in-base64-out
```

### Monitor MQTT Messages

```bash
# Subscribe to all sensor topics
aws iot-data subscribe \
  --topic 'sensors/+/motion' \
  --query 'messages[*].[topic,payload]'
```

### Test IoT Rule

```bash
# Via IoT Test Client in AWS Console
# 1. Go to AWS IoT Core → Test
# 2. Subscribe to topic: sensors/+/motion
# 3. Publish test message
# 4. Verify Lambda function is triggered (check CloudWatch Logs)
```

## Monitoring

### CloudWatch Metrics

- `PublishIn.Success` - Successful publishes
- `PublishIn.AuthError` - Authentication failures
- `RuleMessageThrottled` - Throttled messages
- `RuleNotFound` - Rules with errors

### Alarms

Set up alarms for:
- Auth failures > 5 per minute
- Message throttling
- Rule execution errors

## Troubleshooting

**Device can't connect:**
- Verify certificate is valid and not expired
- Check policy is attached to certificate
- Verify IoT endpoint URL is correct
- Check device clock is synchronized (TLS requires accurate time)

**Messages not reaching Lambda:**
- Verify IoT Rule is enabled
- Check Rule SQL syntax
- Review CloudWatch Logs for Rule execution
- Verify Lambda function has correct permissions

**Authentication errors:**
- Certificate expired or revoked
- Certificate not attached to Thing
- Policy not allowing connection
- Using wrong IoT endpoint

## Resources

- [AWS IoT Core Documentation](https://docs.aws.amazon.com/iot/)
- [IoT Device SDK](https://github.com/aws/aws-iot-device-sdk-embedded-C)
- [IoT Rule Actions](https://docs.aws.amazon.com/iot/latest/developerguide/iot-rule-actions.html)

