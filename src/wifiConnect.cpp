#include <ESP8266WiFi.h>
#include "constants.h"

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

void WifiConnectionStatus()
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

}
