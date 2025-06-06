#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "secrets.h" 

#define ONE_WIRE_BUS 21
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

float temperatureC[10];
float temperatureF[10];
String docName = "";

void setup() {
  Serial.begin(115200);
  delay(1000);

  sensors.begin();

  // Connect to Wi-Fi
  Serial.println("Connecting to Wi-Fi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");

  // Get user-defined doc suffix
  String userInput = "";
  Serial.println("Enter a name to store your Firebase document as test_<your_value>: ");
  while (userInput == "") {
    if (Serial.available()) {
      userInput = Serial.readStringUntil('\n');
      userInput.trim();
    }
  }

  docName = "test_" + userInput;
  Serial.println("Document name will be: " + docName);
  Serial.println("Starting in 5 seconds...");
  delay(5000);

  // Take 10 readings
  for (int i = 0; i < 10; i++) {
    sensors.requestTemperatures();
    float tempC = sensors.getTempCByIndex(0);
    float tempF = tempC * 9.0 / 5.0 + 32.0;

    temperatureC[i] = tempC;
    temperatureF[i] = tempF;

    Serial.printf("Reading %d: %.2f°C / %.2f°F\n", i, tempC, tempF);
    delay(2000);
  }

  // Send to Firebase
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    String url = String("https://") + FIREBASE_HOST + "/brewLogs/" + docName + ".json?auth=" + FIREBASE_AUTH;

    String jsonData = "{";
    for (int i = 0; i < 10; i++) {
      jsonData += "\"reading" + String(i) + "\": {";
      jsonData += "\"celsius\": " + String(temperatureC[i], 2) + ",";
      jsonData += "\"fahrenheit\": " + String(temperatureF[i], 2);
      jsonData += (i < 9) ? "}," : "}";
    }
    jsonData += "}";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.PUT(jsonData);
    if (httpResponseCode > 0) {
      Serial.printf("Firebase upload success. Code: %d\n", httpResponseCode);
    } else {
      Serial.printf("Firebase upload failed. Error: %s\n", http.errorToString(httpResponseCode).c_str());
    }

    http.end();
  }
}

void loop() {
  // Nothing here
}
