-- Device Registration IoT Rule
-- Triggers when devices publish to sensors/+/register topics
-- Extracts sensor ID and forwards to DeviceRegistrationFunction

SELECT 
    *,
    topic(2) as sensorId,
    timestamp() as receivedTimestamp
FROM 'sensors/+/register'

