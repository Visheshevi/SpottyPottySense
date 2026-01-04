
#include <Arduino.h>

#define LED 2

const int ledPin = 32;
const int motionInput = 19;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  Serial.println("Hello, ESP32!");
  pinMode(LED, OUTPUT);
  pinMode(ledPin, OUTPUT);
  pinMode(motionInput, INPUT);
}

void loop() {
  
  int pinState = digitalRead(motionInput);
  if(pinState == HIGH)
  {
    digitalWrite(LED, HIGH);
    digitalWrite(ledPin,HIGH);
  }
  else
  {
    digitalWrite(LED,LOW);
    digitalWrite(ledPin,LOW);
  }

}
