#include <Arduino.h>

#define timeSeconds 2

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


void setup() {
  // put your setup code here, to run once:
  // Serial port for debugging purposes
  Serial.begin(115200);
  // PIR Motion Sensor mode INPUT_PULLUP
  pinMode(motionSensor, INPUT_PULLUP);

  // Set motionSensor pin as interrupt, assign interrupt function and set RISING mode
  attachInterrupt(digitalPinToInterrupt(motionSensor), detectsMovement, RISING);

  // Set LED to LOW
  pinMode(led, OUTPUT);
  digitalWrite(led, LOW);
}

void loop()
 {
    // put your main code here, to run repeatedly:
    // Current time
    now = millis();

    // Turn off the LED after the number of seconds defined in the timeSeconds variable
    if(startTimer && (now - lastTrigger > (timeSeconds*1000))) {
      Serial.println("Motion stopped...");
      digitalWrite(led, LOW);
      startTimer = false;
    }
  
}