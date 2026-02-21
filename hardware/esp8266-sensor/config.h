/**
 * SpottyPottySense Configuration
 * 
 * This file contains DEFAULT settings that are safe to commit to git.
 * 
 * FOR LOCAL CONFIGURATION:
 * 1. Copy config.example.local.h to config.local.h
 * 2. Edit config.local.h with your actual credentials
 * 3. config.local.h is gitignored (never committed)
 * 4. Upload - config.local.h automatically overrides these defaults
 * 
 * ⚠️ DO NOT put real credentials in this file!
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
// FIRMWARE VERSION
// ============================================================================

#define FIRMWARE_VERSION "1.0.0"

// ============================================================================
// DEFAULT CONFIGURATION (Override in config.local.h)
// ============================================================================

// WiFi Configuration - DEFAULTS
#ifndef WIFI_SSID
  #define WIFI_SSID "YOUR_WIFI_SSID"
#endif

#ifndef WIFI_PASSWORD
  #define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#endif

// WiFi connection timeout (milliseconds)
#define WIFI_CONNECT_TIMEOUT 30000  // 30 seconds

// ============================================================================
// AWS IOT CONFIGURATION - DEFAULTS
// ============================================================================

#ifndef AWS_IOT_ENDPOINT
  #define AWS_IOT_ENDPOINT "YOUR_IOT_ENDPOINT.iot.REGION.amazonaws.com"
#endif

#ifndef SENSOR_ID
  #define SENSOR_ID "YOUR_SENSOR_ID"
#endif

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

// ============================================================================
// LOCAL CONFIGURATION OVERRIDE
// ============================================================================
// If config.local.h exists, it will override the defaults above
// This file is gitignored, so your credentials stay private

#if __has_include("config.local.h")
  #include "config.local.h"
  #pragma message "✓ Using config.local.h for credentials"
#else
  #pragma message "⚠️ No config.local.h found - using defaults"
  #pragma message "   Create one: cp config.example.local.h config.local.h"
#endif

#endif // CONFIG_H
