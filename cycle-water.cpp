/*
  ESP32 Water Pump control using an H-Bridge control board.
  Author: Naomi Gonzalez 
  Date: Nov 2024

  Description:
  This sketch allows you to control a KEURIG K25 Water Pump 12V CJWP27-AC12C6B
  using an L298N (H-bridge control baord). It cycles with turing the water
  pump on and off as an intial test to see how much water can be moved
  in a fixed time period. 

  Connections:
  - L298N 
    - Out1 = Red water pump V+
    - Out2 = Black water pump GND
    - +12V = Power supply voltage (12V)
    - GND = Power supply GND; ESP32-S3 GND
    - IN1 = GPIO PIN 16
    - IN2 = GPIO PIN 17
*/

#include <Arduino.h>

#define IN1_PIN 16  
#define IN2_PIN 17  


void setup() {
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);

  // Initialize pump to OFF
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, LOW);
}

void loop() {
  // Turn the pump ON
  digitalWrite(IN1_PIN, HIGH);  
  digitalWrite(IN2_PIN, LOW);
  delay(5000);  

  // Turn the pump OFF
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, LOW);
  delay(5000);  
}
