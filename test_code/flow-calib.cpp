#include <Arduino.h>

// Pin assignments
static const int PUMP_PWM_PIN     = 40;  // L298N IN1
static const int FLOW_SENSOR_PIN  = 10;   // Flow sensor output (through level shifter)
static const int OE_PIN           = 8;   // L298N output enable (active HIGH)

// Interrupt counter
volatile unsigned long pulseCount = 0;

// Flags and variables
bool counting = false;         // Whether we're currently pumping/counting pulses
unsigned long startTime = 0;   // Timestamp (ms) when "start <num>" is received
unsigned long finishTime = 0;  // Timestamp (ms) when space is pressed

// Interrupt Service Routine for flow sensor
void IRAM_ATTR flowISR() {
  pulseCount++;
}

void setup() {
  Serial.begin(115200);

  // Set up pump PWM pin & OE pin
  pinMode(PUMP_PWM_PIN, OUTPUT);
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH);  // Enable output on L298N

  // Tie IN2 of L298N to ground physically, so the pump runs in one direction

  // Set up flow sensor pin and interrupt on RISING edge
  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), flowISR, RISING);

  // Configure an LEDC PWM channel on the ESP32
  //    channel = 0, freq = 1000 Hz, resolution = 8 bits
  ledcSetup(0, 1000, 8);
  ledcAttachPin(PUMP_PWM_PIN, 0);

  Serial.println("Setup complete.\n");
  Serial.println("Type 'start <duty>' (0-255) to run the pump at that duty cycle.");
  Serial.println("Example: 'start 128'");
  Serial.println("Press the space bar (and Enter if needed) to stop the pump.\n");
}

void loop() {

  // If not currently pumping, check if user typed "start X"
  if (!counting) {
    if (Serial.available()) {
      // Read a full line (until newline)
      String input = Serial.readStringUntil('\n');
      input.trim();  // Remove any extra whitespace

      // We expect something like "start 128"
      // 1) Check if it starts with "start"
      // 2) Parse the number after "start "
      if (input.startsWith("start ")) {
        // Extract the substring after "start "
        // e.g., in "start 128", we want "128"
        int spaceIndex = input.indexOf(' ');
        if (spaceIndex != -1) {
          String dutyString = input.substring(spaceIndex + 1);
          dutyString.trim();

          // Convert dutyString to an integer
          int dutyVal = dutyString.toInt();

          // Constrain the duty cycle between 0 and 255
          dutyVal = constrain(dutyVal, 0, 255);

          // Reset pulse count
          pulseCount = 0;

          // Record the start time
          startTime = millis();

          // Turn pump ON at the given duty cycle
          ledcWrite(0, dutyVal);

          Serial.print("Pump ON at duty cycle = ");
          Serial.println(dutyVal);
          Serial.println("Press space (then Enter if needed) to stop the pump.");
          Serial.print("Start time (ms): ");
          Serial.println(startTime);

          counting = true;
        }
      }
    }
  }
  // If currently counting, watch for a space character to stop
  else {
    // Check if there's any serial input
    while (Serial.available()) {
      char c = (char)Serial.read();
      if (c == ' ') {
        // Record finish time
        finishTime = millis();

        // Stop the pump
        ledcWrite(0, 0);

        // Print results
        Serial.println("\nPump OFF.");
        Serial.print("Total pulses counted: ");
        Serial.println(pulseCount);

        Serial.print("Finish time (ms): ");
        Serial.println(finishTime);

        Serial.print("Total duration (ms): ");
        Serial.println(finishTime - startTime);

        Serial.println("\nType 'start <duty>' to run again.");

        counting = false;
      }
    }
  }
}