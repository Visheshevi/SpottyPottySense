#ifndef __CONSTANTS_H__
#define __CONSTANTS_H__

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

#define timeSeconds 1
#define stopAfterMinutes 5
#define motionDetectGap 2 // in minutes
 
// Set GPIOs for LED and PIR Motion Sensor
const int led = 14;
const int motionSensor = 4;

// Timer: Auxiliary variables
extern unsigned long now;
extern unsigned long lastTrigger;
extern boolean startTimer;

// WiFI Creds=entials
extern const char* ssid;
extern const char* password;

// MQTT Credentials
extern const char* mqtt_server;
extern const char* mqtt_user;
extern const char* mqtt_pass;
extern const int mqtt_port;

extern const char* motion_detect_topic;
extern const char* spotify_running_question_topic;
extern const char* spotify_running_answer_topic;

extern WiFiClient espClient;
extern PubSubClient client;

// MQTT function definitions
void publish(const char* topic_name, const char* message);
void setMQTTClient();
bool mqttConnectedStatus();

// WiFi function Defintions
void connectToWifi();
void WifiConnectionStatus();


#endif // __CONSTANTS_H__
