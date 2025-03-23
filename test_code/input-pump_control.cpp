/*
  ESP32 Water Pump Control with User Input
  Author: Naomi Gonzalez 
  Date: Nov 2024

  Description:
  This sketch allows you to control a KEURIG K25 Water Pump 12V CJWP27-AC12C6B
  using an L298N (H-bridge control board). It waits for user input via the Serial Monitor,
  runs the pump for the specified duration in seconds, then turns it off until another input is received.

  Connections:
  - L298N 
    - OUT1 = Red wire water pump V+
    - OUT2 = Black wire water pump GND
    - +12V = Power supply voltage (12V)
    - GND = Power supply GND; ESP32-S3 GND
    - IN1 = GPIO PIN 16
    - IN2 = GPIO PIN 17
*/

#include <Arduino.h>

// Motor Control Pins
#define IN1_PIN 16  
#define IN2_PIN 17  

// Pump Control States
enum PumpState {
  IDLE,
  RUNNING
};

PumpState currentState = IDLE;

unsigned long pumpStartTime = 0;
unsigned long pumpDuration = 0; 

String inputString = "";         
bool stringComplete = false;    

void setup() {
  Serial.begin(115200);

  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);

  // Initialize Pump to OFF
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, LOW);

  inputString.reserve(50); // Space for user input

  Serial.println("-------------------------------------------------");
  Serial.println("ESP32 Water Pump Control");
  Serial.println("Designed to take data to correlate time to flow rate");
  Serial.println("-------------------------------------------------");
  Serial.println("Input pump run duration in seconds and press Enter.");
  Serial.println("Example: To run the pump for 10 seconds, type '10' and press Enter.");
  Serial.println("-------------------------------------------------");
}

void loop() {
  // Manage Pump States
  switch (currentState) {
    case IDLE:
      // Wait for user input to start pump
      if (stringComplete) {
        pumpDuration = parseInput(inputString); 
        if (pumpDuration > 0) {
          digitalWrite(IN1_PIN, HIGH);  
          digitalWrite(IN2_PIN, LOW);
          pumpStartTime = millis();
          currentState = RUNNING;

          Serial.print("Pump ON for ");
          Serial.print(pumpDuration / 1000);
          Serial.println(" seconds.");
        } else {
          Serial.println("Invalid input. Please enter a positive number.");
        }
        // Reset for next input
        inputString = "";
        stringComplete = false;
      }
      break;

    case RUNNING:
      // Check if the pump has run for the desired duration
      if (millis() - pumpStartTime >= pumpDuration) {
        // Turn Pump OFF
        digitalWrite(IN1_PIN, LOW);
        digitalWrite(IN2_PIN, LOW);
        currentState = IDLE;

        Serial.println("Pump OFF.");
        Serial.println("-------------------------------------------------");
        Serial.println("Input pump run duration in seconds and press Enter.");
      }
      break;
  }
}

// Serial Event Handler
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n' || inChar == '\r') {
      stringComplete = true;
      break;
    } else {
      inputString += inChar;
    }
  }
}

// Function to Parse Input String to Duration in Milliseconds
unsigned long parseInput(String input) {
  input.trim(); 
  if (input.length() == 0) return 0;

  unsigned long seconds = input.toInt();
  if (seconds == 0 && input != "0") {
    return 0;
  }
  return seconds * 1000; // Convert to milliseconds
}
