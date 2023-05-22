#include <Arduino.h>
#include "constants.h"
#include "mqttConnect.cpp"
#include "wifiConnect.cpp"

// Checks if motion was detected, sets LED HIGH and starts a timer
IRAM_ATTR void detectsMovement()
{
  digitalWrite(led, HIGH);
  startTimer = true;
  lastTrigger = millis();
  Serial.println("Motion DETECTED!!");
  publish(motion_detect_topic, "Motion Detected in the Bathroom!!!");
}

void setup() 
{
  Serial.begin(115200);
  // PIR Motion Sensor mode INPUT_PULLUP
  pinMode(motionSensor, INPUT_PULLUP);

  // Set motionSensor pin as interrupt, assign interrupt function and set RISING mode
  attachInterrupt(digitalPinToInterrupt(motionSensor), detectsMovement, RISING);

  // Set LED to LOW
  pinMode(led, OUTPUT);
  digitalWrite(led, LOW);

  connectToWifi();
  setMQTTClient();
}

void loop()
{
    WifiConnectionStatus();

    // Current time
    now = millis();

    // Turn off the LED after the number of seconds defined in the timeSeconds variable
    if(startTimer && (now - lastTrigger > (timeSeconds*1000))) {
      Serial.println("Motion stopped...");
      digitalWrite(led, LOW);
      startTimer = false;
    }
  
}