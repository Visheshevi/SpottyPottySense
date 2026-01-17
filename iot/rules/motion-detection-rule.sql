-- Motion Detection IoT Rule
-- Triggers when devices publish to sensors/+/motion topics
-- Extracts sensor ID from topic and forwards to MotionHandlerFunction

SELECT 
    *,
    topic(2) as sensorId,
    timestamp() as receivedTimestamp
FROM 'sensors/+/motion'
WHERE event = 'motion_detected'

