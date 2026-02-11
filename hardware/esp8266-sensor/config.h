/**
 * SpottyPottySense Configuration
 * 
 * Update these settings before uploading firmware.
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
// FIRMWARE VERSION
// ============================================================================

#define FIRMWARE_VERSION "1.0.0"

// ============================================================================
// WIFI CONFIGURATION
// ============================================================================

// TODO: Update with your WiFi credentials
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// WiFi connection timeout (milliseconds)
#define WIFI_CONNECT_TIMEOUT 30000  // 30 seconds

// ============================================================================
// AWS IOT CONFIGURATION
// ============================================================================

// TODO: Update with your AWS IoT Core endpoint
// Get from: AWS IoT Console → Settings → Device data endpoint
// Example: "a3rro0nxekkodu-ats.iot.us-east-2.amazonaws.com"
#define AWS_IOT_ENDPOINT "YOUR_AWS_IOT_ENDPOINT.iot.REGION.amazonaws.com"

// TODO: Update with your sensor ID
// Must match the sensor registered in AWS
#define SENSOR_ID "YOUR_SENSOR_ID"

// MQTT Configuration
#define MQTT_PORT 8883                    // AWS IoT uses port 8883 for MQTTS
#define MQTT_BUFFER_SIZE 512              // Message buffer size
#define MQTT_KEEPALIVE 60                 // MQTT keepalive interval (seconds)
#define MQTT_RECONNECT_DELAY 5000         // Initial reconnect delay (ms)

// MQTT Topics (automatically generated from SENSOR_ID)
// Motion events: sensors/{SENSOR_ID}/motion
// Status updates: sensors/{SENSOR_ID}/status
// Config updates: sensors/{SENSOR_ID}/config

// ============================================================================
// HARDWARE CONFIGURATION
// ============================================================================

// GPIO Pins
#define PIR_PIN D1                        // Motion sensor input (GPIO5)
#define LED_PIN LED_BUILTIN               // Status LED (GPIO2)

// Motion Detection
#define DEBOUNCE_TIME 120000              // 2 minutes in milliseconds
                                          // Prevents rapid re-triggering
                                          // Adjust based on your needs:
                                          // - 60000  = 1 minute
                                          // - 120000 = 2 minutes
                                          // - 180000 = 3 minutes

// ============================================================================
// DEBUG CONFIGURATION
// ============================================================================

// Serial baud rate
#define SERIAL_BAUD 115200

// Enable/disable debug output
#define DEBUG_ENABLED true

// Debug macros
#if DEBUG_ENABLED
  #define DEBUG_PRINT(x) Serial.print(x)
  #define DEBUG_PRINTLN(x) Serial.println(x)
#else
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
#endif

// ============================================================================
// ADVANCED CONFIGURATION
// ============================================================================

// Watchdog timer (optional - for ESP8266 stability)
#define ENABLE_WATCHDOG true
#define WATCHDOG_TIMEOUT 8000             // 8 seconds

// Memory management
#define MIN_FREE_HEAP 8192                // Warn if free heap drops below 8KB

// Time sync retry
#define NTP_RETRY_DELAY 500               // Delay between NTP sync attempts (ms)
#define NTP_MAX_RETRIES 30                // Maximum NTP sync attempts

// TLS Configuration
// Use BearSSL for better memory efficiency on ESP8266
#define USE_BEARSSL true

#endif // CONFIG_H
