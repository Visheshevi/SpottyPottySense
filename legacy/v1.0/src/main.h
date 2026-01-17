#include "constants.h"

const char* motion_detect_topic = "motionDetect";

const char* mqtt_server = "MQTT_SERVER_IP_HERE";
const char* mqtt_user = "MQTT_USER_NAME";
const char* mqtt_pass = "MQTT_PASSWORD";
const int mqtt_port = 1883;

const char* ssid = "SSID_HERE";
const char* password = "PASSWORD_HERE";

unsigned long now = millis();
unsigned long lastTrigger = 0;
boolean startTimer = false;
