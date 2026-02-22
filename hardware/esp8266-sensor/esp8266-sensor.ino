/**
 * SpottyPottySense ESP8266 Motion Sensor
 * 
 * Connects to AWS IoT Core via MQTT over TLS and publishes motion detection events.
 * 
 * Hardware: ESP8266 (NodeMCU/Wemos D1 Mini) + PIR Motion Sensor (HC-SR501)
 * 
 * @author SpottyPottySense Team
 * @version 1.0.0
 */

#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <time.h>
#include <ArduinoJson.h>

// Include configuration and certificates
#include "config.h"
#include "certificates.h"

// ============================================================================
// GLOBAL OBJECTS
// ============================================================================

// BearSSL certificate objects (must be global to persist)
BearSSL::X509List awsCACert(AWS_ROOT_CA);
BearSSL::X509List awsClientCert(AWS_DEVICE_CERT);
BearSSL::PrivateKey awsPrivateKey(AWS_PRIVATE_KEY);

WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

// ============================================================================
// STATE VARIABLES
// ============================================================================

unsigned long lastMotionTime = 0;
unsigned long lastReconnectAttempt = 0;
bool motionDetected = false;
int reconnectDelay = MQTT_RECONNECT_DELAY;

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  // Initialize serial
  Serial.begin(115200);
  delay(100);
  
  Serial.println();
  Serial.println("╔════════════════════════════════════════════════════════╗");
  Serial.println("║      SpottyPottySense ESP8266 Motion Sensor v1.0      ║");
  Serial.println("╚════════════════════════════════════════════════════════╝");
  Serial.println();
  
  // Initialize GPIO
  pinMode(PIR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH); // LED off (inverse logic)
  
  Serial.println("[GPIO] Motion sensor pin: D1 (GPIO5)");
  Serial.println("[GPIO] LED pin: D4 (GPIO2)");
  
  // Connect to WiFi
  connectWiFi();
  
  // Sync time (required for TLS)
  syncTime();
  
  // Configure AWS IoT certificates
  configureCertificates();
  
  // Configure MQTT
  mqttClient.setServer(AWS_IOT_ENDPOINT, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(MQTT_BUFFER_SIZE);
  
  // Connect to AWS IoT
  connectAWSIoT();
  
  Serial.println();
  Serial.println("✓ Initialization complete!");
  Serial.println("✓ Ready to detect motion");
  Serial.println();
  
  // Flash LED to indicate ready
  flashLED(3, 200);
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  // Ensure WiFi is connected
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Connection lost! Reconnecting...");
    connectWiFi();
  }
  
  // Ensure MQTT is connected
  if (!mqttClient.connected()) {
    unsigned long now = millis();
    if (now - lastReconnectAttempt > reconnectDelay) {
      lastReconnectAttempt = now;
      if (connectAWSIoT()) {
        lastReconnectAttempt = 0;
        reconnectDelay = MQTT_RECONNECT_DELAY; // Reset delay
      } else {
        // Exponential backoff
        reconnectDelay = min(reconnectDelay * 2, 60000); // Max 60 seconds
      }
    }
  }
  
  // Process MQTT messages
  mqttClient.loop();
  
  // Check motion sensor
  checkMotion();
  
  // Small delay to prevent tight loop
  delay(100);
}

// ============================================================================
// WIFI FUNCTIONS
// ============================================================================

void connectWiFi() {
  Serial.print("[WiFi] Connecting to: ");
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  unsigned long startAttemptTime = millis();
  
  while (WiFi.status() != WL_CONNECTED && 
         millis() - startAttemptTime < WIFI_CONNECT_TIMEOUT) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println();
    Serial.println("[WiFi] ✗ Connection failed!");
    Serial.println("[WiFi] Restarting in 5 seconds...");
    delay(5000);
    ESP.restart();
  }
  
  Serial.println();
  Serial.println("[WiFi] ✓ Connected!");
  Serial.print("[WiFi] IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("[WiFi] Signal Strength: ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
}

// ============================================================================
// TIME SYNC (Required for TLS)
// ============================================================================

void syncTime() {
  Serial.print("[NTP] Syncing time...");
  
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  
  time_t now = time(nullptr);
  int attempts = 0;
  
  while (now < 8 * 3600 * 2 && attempts < 30) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
    attempts++;
  }
  
  if (now < 8 * 3600 * 2) {
    Serial.println();
    Serial.println("[NTP] ✗ Time sync failed!");
    Serial.println("[NTP] Restarting in 5 seconds...");
    delay(5000);
    ESP.restart();
  }
  
  Serial.println();
  Serial.print("[NTP] ✓ Time synced: ");
  Serial.println(ctime(&now));
}

// ============================================================================
// CERTIFICATE CONFIGURATION
// ============================================================================

void configureCertificates() {
  Serial.println("[TLS] Configuring certificates...");
  
  // Set certificates for secure connection (using global BearSSL objects)
  wifiClient.setTrustAnchors(&awsCACert);
  wifiClient.setClientRSACert(&awsClientCert, &awsPrivateKey);
  
  Serial.println("[TLS] ✓ Certificates configured");
}

// ============================================================================
// AWS IOT MQTT FUNCTIONS
// ============================================================================

bool connectAWSIoT() {
  Serial.print("[AWS IoT] Connecting to ");
  Serial.print(AWS_IOT_ENDPOINT);
  Serial.print(":");
  Serial.println(MQTT_PORT);
  
  // Create client ID with sensor ID
  String clientId = String("SpottyPottySense-") + SENSOR_ID;
  
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("[AWS IoT] ✓ Connected!");
    
    // Subscribe to config topic (optional)
    String configTopic = String("sensors/") + SENSOR_ID + "/config";
    mqttClient.subscribe(configTopic.c_str());
    Serial.print("[MQTT] Subscribed to: ");
    Serial.println(configTopic);
    
    // Publish online status
    publishStatus("online");
    
    return true;
  } else {
    Serial.print("[AWS IoT] ✗ Connection failed, rc=");
    Serial.println(mqttClient.state());
    
    switch (mqttClient.state()) {
      case -4:
        Serial.println("        MQTT_CONNECTION_TIMEOUT");
        break;
      case -3:
        Serial.println("        MQTT_CONNECTION_LOST");
        break;
      case -2:
        Serial.println("        MQTT_CONNECT_FAILED");
        break;
      case -1:
        Serial.println("        MQTT_DISCONNECTED");
        break;
      case 1:
        Serial.println("        MQTT_CONNECT_BAD_PROTOCOL");
        break;
      case 2:
        Serial.println("        MQTT_CONNECT_BAD_CLIENT_ID");
        break;
      case 3:
        Serial.println("        MQTT_CONNECT_UNAVAILABLE");
        break;
      case 4:
        Serial.println("        MQTT_CONNECT_BAD_CREDENTIALS");
        break;
      case 5:
        Serial.println("        MQTT_CONNECT_UNAUTHORIZED");
        break;
    }
    
    return false;
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("[MQTT] Message received on topic: ");
  Serial.println(topic);
  Serial.print("[MQTT] Payload: ");
  
  // Print payload
  for (unsigned int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
  
  // Parse JSON payload (if needed)
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (!error) {
    // Handle configuration updates
    if (doc.containsKey("debounceMinutes")) {
      int debounceMinutes = doc["debounceMinutes"];
      Serial.print("[Config] Updated debounce time: ");
      Serial.print(debounceMinutes);
      Serial.println(" minutes");
      // Note: Would need to update DEBOUNCE_TIME constant
    }
  }
}

// ============================================================================
// MOTION DETECTION
// ============================================================================

void checkMotion() {
  int pirState = digitalRead(PIR_PIN);
  
  if (pirState == HIGH) {
    unsigned long now = millis();
    
    // Debounce: Only publish if enough time has passed
    if (now - lastMotionTime > DEBOUNCE_TIME || lastMotionTime == 0) {
      Serial.println();
      Serial.println("═══════════════════════════════════════════════════════");
      Serial.println("[Motion] ⚡ MOTION DETECTED!");
      Serial.println("═══════════════════════════════════════════════════════");
      
      // Publish motion event
      publishMotionEvent();
      
      // Update last motion time
      lastMotionTime = now;
      
      // LED feedback
      flashLED(2, 100);
    }
  }
}

void publishMotionEvent() {
  // Build MQTT topic
  String topic = String("sensors/") + SENSOR_ID + "/motion";
  
  // Create JSON payload
  StaticJsonDocument<256> doc;
  doc["sensorId"] = SENSOR_ID;
  doc["event"] = "motion_detected";
  doc["timestamp"] = getISO8601Time();
  doc["rssi"] = WiFi.RSSI();
  
  // Add metadata
  JsonObject metadata = doc.createNestedObject("metadata");
  metadata["firmware"] = FIRMWARE_VERSION;
  metadata["uptime"] = millis() / 1000;
  metadata["freeHeap"] = ESP.getFreeHeap();
  
  // Serialize to string
  char buffer[512];
  size_t len = serializeJson(doc, buffer);
  
  // Publish to AWS IoT
  if (mqttClient.publish(topic.c_str(), buffer, len)) {
    Serial.println("[MQTT] ✓ Motion event published");
    Serial.print("[MQTT] Topic: ");
    Serial.println(topic);
    Serial.print("[MQTT] Payload: ");
    Serial.println(buffer);
  } else {
    Serial.println("[MQTT] ✗ Failed to publish motion event");
  }
}

void publishStatus(const char* status) {
  String topic = String("sensors/") + SENSOR_ID + "/status";
  
  StaticJsonDocument<128> doc;
  doc["sensorId"] = SENSOR_ID;
  doc["status"] = status;
  doc["timestamp"] = getISO8601Time();
  doc["ip"] = WiFi.localIP().toString();
  
  char buffer[256];
  serializeJson(doc, buffer);
  
  mqttClient.publish(topic.c_str(), buffer);
  
  Serial.print("[Status] Published: ");
  Serial.println(status);
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

String getISO8601Time() {
  time_t now = time(nullptr);
  struct tm timeinfo;
  gmtime_r(&now, &timeinfo);
  
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  
  return String(buffer);
}

void flashLED(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, LOW);  // LED on (inverse logic)
    delay(delayMs);
    digitalWrite(LED_PIN, HIGH); // LED off
    if (i < times - 1) {
      delay(delayMs);
    }
  }
}
