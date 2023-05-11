#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "constants.h"

// Set GPIOs for LED and PIR Motion Sensor
const int led = 14;
const int motionSensor = 4;

// Timer: Auxiliary variables
unsigned long now = millis();
unsigned long lastTrigger = 0;
boolean startTimer = false;

// Checks if motion was detected, sets LED HIGH and starts a timer
IRAM_ATTR void detectsMovement() {
  digitalWrite(led, HIGH);
  startTimer = true;
  lastTrigger = millis();
  Serial.println("Motion DETECTED!!");
}

/*
* Connect your controller to WiFi
*/
void connectToWifi()
{
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  int retries = 0;

  while((WiFi.status() != WL_CONNECTED) && (retries < 15))
  {
    retries++;
    delay(500);
    Serial.print(".");
  }
  if(retries > 14)
  {
    Serial.println("WiFi connection Failed!!!");
  }

  if(WiFi.status() == WL_CONNECTED)
  {
    Serial.println("WiFi connected!!!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  }
}

void setup() {
  Serial.begin(115200);
  // PIR Motion Sensor mode INPUT_PULLUP
  pinMode(motionSensor, INPUT_PULLUP);

  // Set motionSensor pin as interrupt, assign interrupt function and set RISING mode
  attachInterrupt(digitalPinToInterrupt(motionSensor), detectsMovement, RISING);

  // Set LED to LOW
  pinMode(led, OUTPUT);
  digitalWrite(led, LOW);

  connectToWifi();
}

void loop()
 {
    // Check WiFi connection
    if((WiFi.status() != WL_CONNECTED))
    {
      Serial.println("WiFi disconnected!! Trying to Connect Again");
      WiFi.disconnect();
      connectToWifi();

      if(WiFi.status() != WL_CONNECTED)
      {
        delay(5000);
        return;
      }
      Serial.println("WiFi Connected!!!");
      Serial.print("IP address: ");
      Serial.println(WiFi.localIP());
    }

    // Current time
    now = millis();

    // Turn off the LED after the number of seconds defined in the timeSeconds variable
    if(startTimer && (now - lastTrigger > (timeSeconds*1000))) {
      Serial.println("Motion stopped...");
      digitalWrite(led, LOW);
      startTimer = false;
    }
  
}