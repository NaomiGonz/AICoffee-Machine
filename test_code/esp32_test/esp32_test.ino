// This code is for Arduino IDE using C to generate mock coffee data and send it to a database

#include <WiFi.h>
#include <HTTPClient.h>

// Supabase Configuration
const char* SUPABASE_URL = "https://oalhkndyagbfonwjnqya.supabase.co/rest/v1/coffee_data";
const char* SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9hbGhrbmR5YWdiZm9ud2pucXlhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzEwMTM4OTIsImV4cCI6MjA0NjU4OTg5Mn0.lxSq85mwUwJMlbRlJfX6Z9HoY5r01E2kxW9DYFLvrCQ";

// WiFi Configuration for Eduroam
const char* WIFI_SSID = "Krish";
//const char* WIFI_USERNAME = "kshah26@bu.edu";
const char* WIFI_PASSWORD = "krish999";

void connectToWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi..");
  int timeout = 20;  // seconds
  int startTime = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if ((millis() - startTime) > timeout * 1000) {
      Serial.println("\nFailed to connect to WiFi. Please check your credentials.");
      return;
    }
  }
  Serial.println("\nConnected to WiFi!");
}

String generateMockData() {
  String jsonData = "{";
  jsonData += "\"aroma\": " + String(random(0, 101) / 10.0) + ",";
  jsonData += "\"flavor\": " + String(random(0, 101) / 10.0) + ",";
  jsonData += "\"aftertaste\": " + String(random(0, 101) / 10.0) + ",";
  jsonData += "\"acidity\": " + String(random(0, 101) / 10.0) + ",";
  jsonData += "\"body\": " + String(random(0, 101) / 10.0) + ",";
  jsonData += "\"balance\": " + String(random(0, 101) / 10.0) + ",";
  jsonData += "\"uniformity\": " + String(random(0, 101) / 10.0) + ",";
  jsonData += "\"cup_cleanliness\": " + String(random(0, 101) / 10.0) + ",";
  jsonData += "\"sweetness\": " + String(random(0, 101) / 10.0) + ",";
  jsonData += "\"moisture\": " + String(random(0, 151) / 10.0) + ",";
  jsonData += "\"defects\": " + String(random(0, 6)) + ",";
  jsonData += "\"processing_method\": \"" + String(random(0, 2) == 0 ? "Washed" : "Natural") + "\",";
  jsonData += "\"color\": \"" + String(random(0, 2) == 0 ? "Green" : "Brown") + "\",";
  jsonData += "\"species\": \"" + String(random(0, 2) == 0 ? "Arabica" : "Robusta") + "\",";
  jsonData += "\"owner\": \"John Doe\",";
  jsonData += "\"country_of_origin\": \"Colombia\",";
  jsonData += "\"farm_name\": \"Finca Esperanza\",";
  jsonData += "\"lot_number\": " + String(random(100, 1000)) + ",";
  jsonData += "\"mill\": \"Central Mill\",";
  jsonData += "\"company\": \"Coffee Co.\",";
  jsonData += "\"altitude\": " + String(random(1000, 2001)) + ",";
  jsonData += "\"region\": \"Antioquia\"";
  jsonData += "}";
  return jsonData;
}

void sendDataToSupabase(String data) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SUPABASE_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("apikey", SUPABASE_KEY);
    int httpResponseCode = http.POST(data);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);
      Serial.println(response);
    } else {
      Serial.print("Error on sending POST: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("WiFi Disconnected");
  }
}

void setup() {
  Serial.begin(115200);
  connectToWiFi();
}

void loop() {
  String data = generateMockData();
  sendDataToSupabase(data);
  delay(5000); // Wait for 5 seconds before sending the next batch of data
}
