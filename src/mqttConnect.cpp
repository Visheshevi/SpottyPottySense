#include "constants.h"


void publish(const char* topic_name, const char* message)
{
    client.publish(topic_name, message);
}

void setMQTTClient()
{
  client.setServer(mqtt_server, mqtt_port);
  while (!client.connected()) 
  {
    if (client.connect("ESP8266Client", mqtt_user, mqtt_pass)) 
    {
      Serial.println("Connected to MQTT broker");
    } 
    else 
    {
      Serial.print("Failed to connect to MQTT broker, rc=");
      Serial.print(client.state());
      Serial.println(" Retrying in 5 seconds...");
      delay(5000);
    }
  }
}