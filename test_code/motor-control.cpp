/*
  ESP32 Motor Control using ESC with 5kHz Signal
  Author: Naomi Gonzalez
  Date: Nov 2024

  Description:
  This sketch allows you to control the speed of a motor via an ESC
  using a 5kHz PWM signal. The user can input a desired speed percentage
  (0-100%) through the Serial Monitor.

  Connections:
  - Readytosky 40A ESC 
    - Port C = Blue motor wire
    - Port B = Red motor wire
    - Port A = Black motor wire
    - Black Wire (-) = Ground 
    - Red Wire (+) = Power supply voltage (24V)
    - white skinny = GPIO PIN 18
    - black skinny = Ground 
*/
#include <Arduino.h>

// PWM Configuration
const int pwmFreq = 5000;        
const int pwmResolution = 8;     // 8-bit resolution (0-255)
const int pwmChannel = 0;        // LEDC channel (0-15)
const int pwmPin = 18;           

// Speed Control Variables
int speedPercentage = 0;         // User-defined speed (0-100%)
int pwmDuty = 0;                 // Calculated PWM duty cycle

// Timing Variables for Arming Sequence
unsigned long armingStartTime = 0;
bool isArmed = false;

void setup() {
  Serial.begin(115200);
  // Wait for serial signal 
  while (!Serial) {
    ; 
  }

  Serial.println("ESP32 ReadyToSky 40A ESC Motor Control with 5kHz PWM");
  ledcSetup(pwmChannel, pwmFreq, pwmResolution);
  ledcAttachPin(pwmPin, pwmChannel);
  ledcWrite(pwmChannel, 0);
}

void loop() {

  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n'); 
    input.trim(); 

    int inputValue = input.toInt();

    if (inputValue >= 0 && inputValue <= 100) {
      speedPercentage = inputValue;
      // Map speed percentage to PWM duty cycle
      pwmDuty = map(speedPercentage, 0, 100, 0, 255); // 8-bit resolution

      ledcWrite(pwmChannel, pwmDuty);

      Serial.print("Speed set to ");
      Serial.print(speedPercentage);
      Serial.println("%");
    } else {
      Serial.println("Invalid input. Please enter a value between 0 and 100.");
    }

    Serial.println("Enter speed percentage (0-100):");
  }

  delay(100);

}
