#ifndef __CONSTANTS_H__
#define __CONSTANTS_H__

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

#define timeSeconds 2
 
// Set GPIOs for LED and PIR Motion Sensor
const int led = 14;
const int motionSensor = 4;

// Timer: Auxiliary variables
unsigned long now = millis();
unsigned long lastTrigger = 0;
boolean startTimer = false;

// WiFI Creds=entials
const char* ssid = "YOUR_SSID_HERE";
const char* password = "WIFI_PASSWORD_HERE";

// MQTT Credentials
const char* mqtt_server = "MQTT_SERVER_IP_HERE";
const char* mqtt_user = "MQTT_USER_NAME";
const char* mqtt_pass = "MQTT_PASSWORD";
const int mqtt_port = 1883;

const char* motion_detect_topic = "motionDetect";

WiFiClient espClient;
PubSubClient client(espClient);
#endif // __CONSTANTS_H__