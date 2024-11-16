/*
  ESP32 Motor Control using ESC with 5kHz Signal and Supabase Integration
  Author: Naomi Gonzalez and Krish Shah
  Date: Nov 2024

  Description:
  This sketch allows you to control the speed of a motor via an ESC
  using a 5kHz PWM signal. The user can input a desired speed percentage
  (0-100%) through the Serial Monitor. It also uploads the speed percentage
  and the time between speed settings to a Supabase database.

  Connections:
  - Readytosky 40A ESC 
    - Port C = Blue motor wire
    - Port B = Red motor wire
    - Port A = Black motor wire
    - Black Wire (-) = Ground 
    - Red Wire (+) = Power supply voltage (24V)
    - White skinny = GPIO PIN 18
    - Black skinny = Ground 
*/

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// PWM Configuration
const int pwmFreq = 5000;
const int pwmResolution = 8;     // 8-bit resolution (0-255)
const int pwmChannel = 0;        // LEDC channel (0-15)
const int pwmPin = 18;

// WiFi Configuration
const char* ssid = "Sebastian_Izzy";
const char* password = "9176913522";

// Supabase Configuration
const char* supabaseUrl = "https://oalhkndyagbfonwjnqya.supabase.co/rest/v1/esc_motor_data_test";
const char* supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9hbGhrbmR5YWdiZm9ud2pucXlhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzEwMTM4OTIsImV4cCI6MjA0NjU4OTg5Mn0.lxSq85mwUwJMlbRlJfX6Z9HoY5r01E2kxW9DYFLvrCQ";

// Speed Control Variables
int speedPercentage = 0;         // User-defined speed (0-100%)
int pwmDuty = 0;                 // Calculated PWM duty cycle

// Timing Variables
unsigned long previousTime = 0;
unsigned long currentTime = 0;
double timeDifference = 0.0;

void setup() {
  Serial.begin(115200);

  // Wait for serial signal 
  while (!Serial) {
    ; 
  }

  Serial.println("ESP32 ReadyToSky 40A ESC Motor Control with 5kHz PWM and Supabase");

  // Initialize PWM
  ledcSetup(pwmChannel, pwmFreq, pwmResolution);
  ledcAttachPin(pwmPin, pwmChannel);
  ledcWrite(pwmChannel, 0);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("Connected to WiFi");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n'); 
    input.trim(); 

    int inputValue = input.toInt();

    if (inputValue >= 0 && inputValue <= 100) {
      // Update timing
      currentTime = millis();
      timeDifference = (currentTime - previousTime) / 1000.0;
      previousTime = currentTime;

      // Update speed
      speedPercentage = inputValue;
      pwmDuty = map(speedPercentage, 0, 100, 194, 253); // Map speed percentage to PWM duty cycle
      ledcWrite(pwmChannel, pwmDuty);

      Serial.print("Speed set to ");
      Serial.print(speedPercentage);
      Serial.println("%");
      Serial.print("Time since last input: ");
      Serial.print(timeDifference, 3);
      Serial.println(" seconds");

      // Upload data to Supabase
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(supabaseUrl);
        http.addHeader("Content-Type", "application/json");
        http.addHeader("apikey", supabaseKey);

        StaticJsonDocument<256> json;
        json["speed_percentage"] = speedPercentage;
        json["time_difference_s"] = timeDifference;

        String requestBody;
        serializeJson(json, requestBody);

        int httpResponseCode = http.POST(requestBody);

        if (httpResponseCode > 0) {
          Serial.print("Data uploaded: ");
          Serial.println(httpResponseCode);
        } else {
          Serial.print("Error uploading data: ");
          Serial.println(http.errorToString(httpResponseCode));
        }

        http.end();
      } else {
        Serial.println("WiFi not connected. Unable to upload data.");
      }

    } else {
      Serial.println("Invalid input. Please enter a value between 0 and 100.");
    }

    Serial.println("Enter speed percentage (0-100):");
  }

  delay(100);
}

