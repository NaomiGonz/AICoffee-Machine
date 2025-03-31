#include <Arduino.h>
#include "VescUart.h"  // from https://github.com/SolidGeek/VescUart

// Pin definitions for your two VESCs
#define VESC1_RX_PIN 16
#define VESC1_TX_PIN 17
#define VESC2_RX_PIN 12
#define VESC2_TX_PIN 13

// Serial baud rate for both USB and UART
#define SERIAL_BAUD 115200

// ===========================
// Ramping Configuration
// ===========================

// VESC1 (RPM) ramp: we move in increments of ±1 RPM, every 1000 microseconds.
#define RPM_STEP_SIZE          7.0f      // how many RPM to change per step
#define RPM_STEP_INTERVAL_US   100UL    // time between steps, in microseconds

// VESC2 (duty) ramp: we move in increments of ±0.001 duty, every 500 microseconds.
#define DUTY_STEP_SIZE         0.001f
#define DUTY_STEP_INTERVAL_US  500UL

// ===========================
// Create VescUart objects
// ===========================
VescUart vesc1;  // uses RPM control
VescUart vesc2;  // uses duty control

// Current vs. target setpoints
float currentRpm1 = 0.0f;
float targetRpm1  = 0.0f;

float currentDuty2 = 0.0f;
float targetDuty2  = 0.0f;

// Timestamps for stepping
uint32_t lastRpmStepTime  = 0;
uint32_t lastDutyStepTime = 0;

// For reading user commands over USB serial
String inputBuffer = "";

//-------------------------------------------------
// Setup
//-------------------------------------------------
void setup() {
  Serial.begin(SERIAL_BAUD);

  // Start hardware serial ports for VESC1 & VESC2
  Serial1.begin(SERIAL_BAUD, SERIAL_8N1, VESC1_RX_PIN, VESC1_TX_PIN);
  Serial2.begin(SERIAL_BAUD, SERIAL_8N1, VESC2_RX_PIN, VESC2_TX_PIN);

  // Assign each VESCUart object to its hardware serial
  vesc1.setSerialPort(&Serial1);
  vesc2.setSerialPort(&Serial2);

  Serial.println("Commands:");
  Serial.println("  vesc1 <rpm>   e.g. 'vesc1 3600'");
  Serial.println("  vesc2 <duty>  e.g. 'vesc2 0.5'");
  Serial.println("Ramp rules:");
  Serial.println("  VESC1: steps ±7 RPM every 100µs");
  Serial.println("  VESC2: steps ±0.001 duty every 500µs");
}

//-------------------------------------------------
// Stepping Functions
//-------------------------------------------------
void stepRpm() {
  // Move currentRpm1 toward targetRpm1 by RPM_STEP_SIZE
  float diff = targetRpm1 - currentRpm1;
  if (fabs(diff) <= RPM_STEP_SIZE) {
    currentRpm1 = targetRpm1;  // close enough, snap to target
  } else {
    currentRpm1 += (diff > 0 ? RPM_STEP_SIZE : -RPM_STEP_SIZE);
  }
}

void stepDuty() {
  // Move currentDuty2 toward targetDuty2 by DUTY_STEP_SIZE
  float diff = targetDuty2 - currentDuty2;
  if (fabs(diff) <= DUTY_STEP_SIZE) {
    currentDuty2 = targetDuty2;  // close enough, snap
  } else {
    currentDuty2 += (diff > 0 ? DUTY_STEP_SIZE : -DUTY_STEP_SIZE);
  }
}

//-------------------------------------------------
// Loop
//-------------------------------------------------
void loop() {
  // Read any user input from USB Serial
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n') {
      inputBuffer.trim();
      if (inputBuffer.length() > 0) {
        // Process the command
        int spaceIndex = inputBuffer.indexOf(' ');
        if (spaceIndex == -1) {
          Serial.println("Invalid format. Use 'vesc1 <rpm>' or 'vesc2 <duty>'");
        } else {
          String cmd = inputBuffer.substring(0, spaceIndex);
          float value = inputBuffer.substring(spaceIndex + 1).toFloat();

          if (cmd.equalsIgnoreCase("vesc1")) {
            // This is an RPM command
            targetRpm1 = value;
            Serial.print("Target RPM for VESC1 set to: ");
            Serial.println(targetRpm1);

          } else if (cmd.equalsIgnoreCase("vesc2")) {
            // This is a duty command
            if (value > 1.0f)  value = 1.0f;
            if (value < -1.0f) value = -1.0f;
            targetDuty2 = value;
            Serial.print("Target duty for VESC2 set to: ");
            Serial.println(targetDuty2);

          } else {
            Serial.println("Unknown target. Use 'vesc1' or 'vesc2'.");
          }
        }
      }
      inputBuffer = "";
    } else {
      inputBuffer += c;
    }
  }

  // Check time & step the RPM if it's time
  uint32_t now = micros();

  // Step VESC1 (RPM) if enough microseconds passed
  if ((now - lastRpmStepTime) >= RPM_STEP_INTERVAL_US) {
    stepRpm();
    lastRpmStepTime = now;
  }

  // Step VESC2 (duty) if enough microseconds passed
  if ((now - lastDutyStepTime) >= DUTY_STEP_INTERVAL_US) {
    stepDuty();
    lastDutyStepTime = now;
  }

  // Send updated commands to VESCs
  vesc1.setRPM((int32_t)currentRpm1);
  vesc2.setDuty(currentDuty2);


  delay(1);
}
