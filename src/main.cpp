#include "main.h"


WiFiClient espClient;
PubSubClient client(espClient);

int time_started = 0;
int stopTimeAfter = stopAfterMinutes*60;
bool spotifyStopped = true;
bool initialDelayDone = false;

const unsigned long motion_detect_gap = motionDetectGap * 60 * 1000;

// Checks if motion was detected, sets LED HIGH and starts a timer
IRAM_ATTR void detectsMovement()
{
  if(!initialDelayDone || (millis() - lastTrigger >= motion_detect_gap))
  {
    if(!initialDelayDone)
      initialDelayDone = true;
    digitalWrite(led, HIGH);
    startTimer = true;
    lastTrigger = millis();
    Serial.println("Motion DETECTED!!");
    publish(motion_detect_topic, "motion detected");
    spotifyStopped = false;
  }
  else
    Serial.println("Motion Detected but it is too soon, ignoring the motion...");
  // publish(spotify_running_question_topic,"is spotify running?");
  
}


void setup() 
{
  Serial.begin(115200);
  // PIR Motion Sensor mode INPUT_PULLUP
  pinMode(motionSensor, INPUT_PULLUP);

  // Set LED to LOW
  pinMode(led, OUTPUT);
  digitalWrite(led, LOW);

  connectToWifi();
  setMQTTClient();

  // Set motionSensor pin as interrupt, assign interrupt function and set RISING mode
  attachInterrupt(digitalPinToInterrupt(motionSensor), detectsMovement, RISING);
}

void loop()
{
    WifiConnectionStatus();
    client.setKeepAlive(5);
    if(!mqttConnectedStatus())
    {
      setMQTTClient();
      client.subscribe(spotify_running_answer_topic);
    
    }
    client.loop();
    // Current time
    now = millis();

    // Turn off the LED after the number of seconds defined in the timeSeconds variable
    if(startTimer && (now - lastTrigger > (timeSeconds*1000))) {
      digitalWrite(led, LOW);
      startTimer = false;
    }

    

    long curr_time = millis();
    // Stop spotify if there has been no motion in some time
    if(!spotifyStopped && (curr_time - lastTrigger > stopTimeAfter*1000))
    {     
      publish(motion_detect_topic, "no motion detected for sometime");
      String message = "No motion was detected for " + String(stopAfterMinutes) + " minutes, so we stopped spotify"; 
      Serial.println(message);
      spotifyStopped = true;
    } 
}
