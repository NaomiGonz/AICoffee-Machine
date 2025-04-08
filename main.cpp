#include <Arduino.h>
#include <math.h>       // For pow() in pump control
#include <ESP32Servo.h> // For servos
#include "VescUart.h"   // For VESC control
#include <ctype.h>      // For toupper()

// --- Operation Mode ---
// #define WEB_MODE      // Uncomment for Web Server control
#define SERIAL_MODE // Uncomment for Serial Monitor control

#ifdef WEB_MODE
#include <WiFi.h>
#include <WebServer.h>
// #include <ESPmDNS.h> // Optional: uncomment if you want mDNS and add MDNS.update() in loop
#endif

// ==========================================================
// --- WiFi Credentials (if WEB_MODE enabled) ---
// ==========================================================
#ifdef WEB_MODE
const char* ssid = "Sebastian_Izzy"; // Replace with your WiFi SSID
const char* password = "99999999"; // Replace with your WiFi Password
WebServer server(80);
#endif

// ==========================================================
// --- Pin Definitions  ---
// ==========================================================

// VESC Control (Check your actual VESC connections)
// Assuming VESC1=Grinder/Duty, VESC2=Drum/RPM based on previous state
const int VESC1_RX_PIN = 12; // Serial1 RX for GRINDER Motor VESC (Duty)
const int VESC1_TX_PIN = 13; // Serial1 TX for GRINDER Motor VESC (Duty)
const int VESC2_RX_PIN = 16; // Serial2 RX for DRUM Motor VESC (RPM)
const int VESC2_TX_PIN = 17; // Serial2 TX for DRUM Motor VESC (RPM)

// Heater Control
const int HEATER_PIN = 38; // Heater PWM pin

// Logic Level Shifter Enable Pin (Active HIGH)
const int OE_PIN = 8; // Used for Flow Sensor and Servos (if applicable)

// Water Pump Control (L298N or similar driver)
const int PUMP_PWM_PIN    = 40; // Pin connected to PWM input of pump driver
const int FLOW_SENSOR_PIN = 10; // Flow sensor interrupt pin

// Servo Control Pins
const int SERVO_PIN_A = 4;
const int SERVO_PIN_B = 5;
const int SERVO_PIN_C = 6;
const int SERVO_PIN_D = 7;

// ==========================================================
// --- Configuration & Calibration ---
// ==========================================================

// Serial Baud Rate
#define SERIAL_BAUD 115200

// PWM Configuration (Heater/Pump)
#define PWM_FREQ 5000 // PWM Frequency for Heater/Pump
#define PWM_RES 8     // PWM Resolution (0-255)
enum PWMLedcChannels {
  PUMP_LEDC_CHANNEL   = 4, // LEDC Channel for Pump (Changed from 0)
  HEATER_LEDC_CHANNEL = 5  // LEDC Channel for Heater (Changed from 1)
};

// VESC Ramping Configuration (VESC1=Grinder/Duty, VESC2=Drum/RPM)
#define DUTY_STEP_SIZE         0.001f // Grinder motor (VESC1) Duty step
#define DUTY_STEP_INTERVAL_US  500UL  // Grinder motor (VESC1) step interval (micros)
#define RPM_STEP_SIZE          7.0f   // Drum motor (VESC2) RPM step
#define RPM_STEP_INTERVAL_US   100UL  // Drum motor (VESC2) step interval (micros)


// Water Pump Flow Sensor Calibration (Replace with your specific sensor calibration)
// Ticks/mL = -0.0792 * (FlowRate)^2 + 1.0238 * (FlowRate) + 1.2755
// FlowRate (mL/s) = 0.0343 * Duty - 1.0155  => Duty = (FlowRate + 1.0155) / 0.0343

// Water Pump PID Controller Gains (Needs tuning for your specific pump/setup)
float kp = 15.0; // Proportional gain
float ki = 30.0; // Integral gain
float kd = 0.5;  // Derivative gain
float maxIntegral = 100.0; // Anti-windup limit for integral term

// Water Pump Control Intervals
const unsigned long flowCalcInterval = 100; // ms (How often to recalculate flow rate)
const unsigned long controlInterval = 50;   // ms (How often to run PID controller)
const unsigned long PULSE_PRINT_INTERVAL = 500; // ms (How often to print pulse count during pumping)

// --- Servo Speed/Control Definitions (Adjust speeds 0-180, 90=stop for continuous) ---
const int SERVO_STOP_SPEED = 90;
// Speeds based on previous state:
const int SERVO_A_FORWARD_SPEED = 135;
const int SERVO_A_REVERSE_SPEED = 45;
const int SERVO_B_FORWARD_SPEED = 135;
const int SERVO_B_REVERSE_SPEED = 45;
const int SERVO_C_FORWARD_SPEED = 135;
const int SERVO_C_REVERSE_SPEED = 45;
const int SERVO_D_FORWARD_SPEED = 45;
const int SERVO_D_REVERSE_SPEED = 135;

// --- Servo Periodic Motion Parameters ---
const int SERVO_PERIOD_SECONDS = 5;      // Total period duration in seconds
const unsigned long SERVO_PERIOD_MS = SERVO_PERIOD_SECONDS * 1000UL; // Period in milliseconds
const float FORWARD_DUTY_CYCLE = 0.90; // 90% of the period forward
const float REVERSE_DUTY_CYCLE = 0.10; // 10% of the period reverse
// Calculated durations for convenience
const unsigned long FORWARD_DURATION_MS = (unsigned long)(SERVO_PERIOD_MS * FORWARD_DUTY_CYCLE);
const unsigned long REVERSE_DURATION_MS = (unsigned long)(SERVO_PERIOD_MS * REVERSE_DUTY_CYCLE);

// Coffee Machine Safety Parameters
#define HEATER_TIMEOUT 5000     // Heater auto-off if pump not used (ms)
#define POST_PUMP_COOLDOWN 1000 // Heater off delay after pump stops (ms)
#define QUEUE_SIZE 20           // Command queue capacity

// ==========================================================
// --- Global Variables & Objects ---
// ==========================================================

// VESC Objects and State (VESC1=Grinder/Duty, VESC2=Drum/RPM)
VescUart vesc1; // Grinder Motor (Duty Control)
VescUart vesc2; // Drum Motor (RPM Control)
float currentDuty1 = 0.0f; // Current Duty for VESC1 (Grinder)
float targetDuty1  = 0.0f; // Target Duty for VESC1 (Grinder)
float currentRpm2 = 0.0f; // Current RPM for VESC2 (Drum)
float targetRpm2  = 0.0f; // Target RPM for VESC2 (Drum)
uint32_t lastDutyStepTime = 0; // Timer for VESC1 duty stepping
uint32_t lastRpmStepTime  = 0; // Timer for VESC2 RPM stepping


// Water Pump State & Control Variables
volatile unsigned long pulseCount = 0; // Updated by ISR
unsigned long lastPulseCount = 0;      // For flow rate calculation
float dispensedVolumeML = 0.0;         // Calculated dispensed volume
float currentFlowRateMLPS = 0.0;       // Calculated current flow rate
float targetVolumeML = 0.0;            // Target volume from P command
float targetFlowRateMLPS = 0.0;        // Target flow rate from P command
bool dispensingActive = false;         // Flag indicating pump is running
unsigned long lastFlowCalcTime = 0;    // Timer for flow calculation interval
unsigned long lastControlTime = 0;     // Timer for PID control interval
unsigned long lastPulsePrintTime = 0;  // Timer for printing pulse count during dispense
float pidError = 0.0;                  // PID error term
float lastError = 0.0;                 // PID previous error (for derivative)
float integralError = 0.0;             // PID integral term
float derivativeError = 0.0;           // PID derivative term
float pidOutput = 0.0;                 // PID output contribution
int feedforwardDuty = 0;               // Feedforward duty contribution
unsigned long dispenseStartTime = 0;   // Time when dispense started

// Servo Objects
Servo servoA;
Servo servoB;
Servo servoC;
Servo servoD;

// Servo State Management Structure
struct ServoControlState {
  Servo& servoObject;         // Reference to the actual Servo object
  const int forwardSpeed;     // Forward speed for this specific servo
  const int reverseSpeed;     // Reverse speed for this specific servo
  bool isRunning;             // Is the servo currently commanded to run?
  unsigned long stopTime;     // millis() value when the servo should stop completely
  unsigned long periodStartTime; // millis() value when the current forward/reverse period started
  bool isForward;             // Is the servo currently in the forward phase of the period?
  char id;                    // Identifier ('A', 'B', 'C', 'D')
};

// Create state instances for each servo
ServoControlState servoAState = {servoA, SERVO_A_FORWARD_SPEED, SERVO_A_REVERSE_SPEED, false, 0, 0, true, 'A'};
ServoControlState servoBState = {servoB, SERVO_B_FORWARD_SPEED, SERVO_B_REVERSE_SPEED, false, 0, 0, true, 'B'};
ServoControlState servoCState = {servoC, SERVO_C_FORWARD_SPEED, SERVO_C_REVERSE_SPEED, false, 0, 0, true, 'C'};
ServoControlState servoDState = {servoD, SERVO_D_FORWARD_SPEED, SERVO_D_REVERSE_SPEED, false, 0, 0, true, 'D'};

// Coffee Machine State & Command Queue
bool heaterActive = false;             // Flag indicating heater is ON
bool pumpUsedSinceHeaterOn = false;    // Flag for heater safety timeout
unsigned long heaterStartTime = 0;     // Time heater was turned ON
unsigned long generalDelayEndTime = 0; // Time when 'D' command delay finishes

// Command structure and queue definitions
enum CommandType { CMD_R, CMD_G, CMD_P, CMD_H, CMD_S, CMD_D, CMD_INVALID }; // R=Drum RPM, G=Grinder Duty
struct Command {
  CommandType type;
  float value1 = 0; // R:RPM, G:Duty, P:Volume, H:Power%, S:Duration(sec), D:Delay(ms)
  float value2 = 0; // P:Flow Rate
  char id = ' ';    // S: Servo ID (A, B, C, D)
};
Command cmdQueue[QUEUE_SIZE];          // Array to hold commands
int queueFront = 0, queueRear = 0, queueCount = 0; // Queue pointers and count

// Serial Input Buffer
String serialInputBuffer = "";

// Function Prototypes
void updateServo(ServoControlState& state);
void checkSafetyFeatures();
void handleRoot();
void handleCommand();
void handleStatus();
void handleNotFound();

// ==========================================================
// --- Interrupt Service Routines (For Flow Rate) ---
// ==========================================================
// This function is called by the hardware interrupt on every RISING edge from the flow sensor
void IRAM_ATTR flowISR() {
  pulseCount++; // Increment the counter (must be fast and non-blocking)
}

// ==========================================================
// --- Helper Functions ---
// ==========================================================

// --- Water Pump Helpers ---
// Calculates expected Ticks/mL based on a given flow rate using the calibration curve
float getTicksPerML(float flowRate) {
  float ticks = -0.0792 * pow(flowRate, 2) + 1.0238 * flowRate + 1.2755;
  // Prevent division by zero or nonsensical values if flow is very low or calculation fails
  if (ticks <= 0.1) {
      // Fallback: If current flow is near zero, estimate using the target rate
      if (flowRate < 0.1 && targetFlowRateMLPS > 0.1) {
          ticks = -0.0792 * pow(targetFlowRateMLPS, 2) + 1.0238 * targetFlowRateMLPS + 1.2755;
          if (ticks <= 0.1) return 1.0; // Absolute fallback if target also gives bad value
          return ticks;
      }
      return 1.0; // Default fallback if calculation is non-positive
  }
  return ticks;
}

// Calculates estimated PWM duty cycle needed for a target flow rate (Feedforward)
int calculateFeedforwardDuty(float targetRate) {
  if (targetRate <= 0) return 0; // No duty for zero or negative flow
  // Invert the flow rate vs duty equation: Duty = (FlowRate + 1.0155) / 0.0343
  float dutyFloat = (targetRate + 1.0155) / 0.0343;
  return constrain((int)round(dutyFloat), 0, 255); // Round and clamp to 0-255
}

// --- VESC Ramping Helpers (VESC1=Grinder/Duty, VESC2=Drum/RPM) ---
// Gradually steps the current duty towards the target duty for VESC1
void stepDuty1() {
    float diff = targetDuty1 - currentDuty1;
    if (fabs(diff) <= DUTY_STEP_SIZE) {
        currentDuty1 = targetDuty1; // Snap to target if close enough
    } else {
        currentDuty1 += (diff > 0 ? DUTY_STEP_SIZE : -DUTY_STEP_SIZE); // Increment or decrement
    }
    currentDuty1 = constrain(currentDuty1, -1.0f, 1.0f); // Ensure within valid range
}

// Gradually steps the current RPM towards the target RPM for VESC2
void stepRpm2() {
    float diff = targetRpm2 - currentRpm2;
    if (fabs(diff) <= RPM_STEP_SIZE) {
        currentRpm2 = targetRpm2; // Snap to target if close enough
    } else {
        currentRpm2 += (diff > 0 ? RPM_STEP_SIZE : -RPM_STEP_SIZE); // Increment or decrement
    }
    // Add constrain here if there's a max RPM: currentRpm2 = constrain(currentRpm2, -MAX_RPM, MAX_RPM);
}

// --- Command Processing Helpers ---
// Parses a single command token (e.g., "R-1000", "P-50-2.5") into a Command struct
Command parseToken(const String& token) {
  Command cmd; // Create a command object
  cmd.type = CMD_INVALID; // Default to invalid

  // Basic validation: must be at least 3 chars (e.g., R-0) and have '-' at index 1
  if (token.length() < 3 || token[1] != '-') {
      // Optionally print error for malformed tokens, but can be noisy
      // Serial.println("Invalid format (must be X-...). Token: " + token);
      return cmd;
   }

  char cmdType = toupper(token[0]); // Get command type (R, G, P, H, S, D)
  String params = token.substring(2); // Extract parameters after "X-"

  // Parse based on command type
  switch (cmdType) {
    case 'R': // R-<rpm> (Drum RPM)
      cmd.type = CMD_R;
      cmd.value1 = params.toFloat();
      break;
    case 'G': // G-<duty> (Grinder Duty)
      cmd.type = CMD_G;
      cmd.value1 = params.toFloat();
      if (cmd.value1 < -1.0 || cmd.value1 > 1.0) {
         Serial.println("Warning: Grinder Duty " + String(cmd.value1) + " out of range (-1.0 to 1.0). Clamping may occur.");
         // Optionally clamp here: cmd.value1 = constrain(cmd.value1, -1.0f, 1.0f);
      }
      break;
    case 'P': // P-<volume>-<rate>
      { // Use block scope for local variable dashIndex
        int dashIndex = params.indexOf('-'); // Find the dash separating volume and rate
        if (dashIndex != -1) { // Check if dash was found
          cmd.type = CMD_P;
          cmd.value1 = params.substring(0, dashIndex).toFloat(); // Volume is before the dash
          cmd.value2 = params.substring(dashIndex + 1).toFloat(); // Rate is after the dash
          // Validate parsed values
          if (cmd.value1 <= 0 || cmd.value2 <= 0) {
             Serial.println("Invalid P command values (volume and rate must be > 0). Token: " + token);
             cmd.type = CMD_INVALID; // Mark as invalid if values are not positive
          }
        } else {
           Serial.println("Invalid P command format (missing dash between volume and rate). Token: " + token);
           cmd.type = CMD_INVALID; // Mark as invalid if format is wrong
        }
      }
      break;
    case 'H': // H-<power%>
      cmd.type = CMD_H;
      cmd.value1 = params.toFloat(); // Power percentage
      // Validate power range
      if (cmd.value1 < 0 || cmd.value1 > 100) {
         Serial.println("Invalid H command value (must be 0-100). Token: " + token);
         cmd.type = CMD_INVALID;
      }
      break;
    case 'S': // S-<id>-<time_sec>
      { // Block scope for local variables
         int dashIndex = params.indexOf('-'); // Find dash separating ID and time
         // Check format: Dash must be at index 1 (e.g., "A-5") and string must continue after dash
         if (dashIndex == 1 && params.length() > dashIndex + 1) {
            cmd.id = toupper(params[0]); // Servo ID (A, B, C, D)
            float durationSec = params.substring(dashIndex + 1).toFloat(); // Duration in seconds

            // Validate ID and duration
            if ((cmd.id >= 'A' && cmd.id <= 'D') && durationSec > 0) {
                cmd.type = CMD_S;
                cmd.value1 = durationSec; // Store duration in SECONDS in value1
            } else {
                Serial.println("Invalid S command values (ID must be A-D, time > 0 sec). Token: " + token);
                cmd.type = CMD_INVALID; // Mark invalid if validation fails
            }
         } else {
             Serial.println("Invalid S command format (expecting S-ID-time_sec). Token: " + token);
             cmd.type = CMD_INVALID; // Mark invalid if format is wrong
         }
      }
      break;
    case 'D': // D-<time_ms>
      cmd.type = CMD_D;
      cmd.value1 = params.toFloat(); // Delay time in milliseconds
      // Validate delay time
      if (cmd.value1 <= 0) {
         Serial.println("Invalid D command value (must be > 0 ms). Token: " + token);
         cmd.type = CMD_INVALID;
      }
      break;
    default: // Unknown command type
      Serial.println("Unknown command type '" + String(cmdType) + "'. Token: " + token);
      // cmd.type remains CMD_INVALID
      break;
  }
  return cmd; // Return the parsed (or invalid) command struct
}

// Counts the number of valid command tokens within a space-separated string
// Used to check if the queue has enough space *before* trying to add commands.
int countValidCommandsInString(const String& input) {
    String currentToken;
    int validCount = 0;
    for (int i = 0; i < input.length(); i++) {
        // Check for space delimiter or end of string
        if (input[i] == ' ' || i == input.length() - 1) {
            // Include the last character if it's not a space
            if (i == input.length() - 1 && input[i] != ' ') {
                currentToken += input[i];
            }
            currentToken.trim(); // Remove leading/trailing whitespace from the token
            if (currentToken.length() > 0) {
                // Parse the token just to check its validity
                if (parseToken(currentToken).type != CMD_INVALID) {
                    validCount++; // Increment count if valid
                }
            }
            currentToken = ""; // Reset for the next token
        } else {
            currentToken += input[i]; // Build the current token character by character
        }
    }
    return validCount;
}

// Parses a command string and adds *valid* commands to the queue.
// Assumes space availability has been pre-checked using countValidCommandsInString.
void processAndEnqueueCommands(const String& input) {
    String currentToken;
    int cmdAddedCount = 0;
    for (int i = 0; i < input.length(); i++) {
        // Check for space delimiter or end of string
        if (input[i] == ' ' || i == input.length() - 1) {
            // Include the last character if it's not a space
            if (i == input.length() - 1 && input[i] != ' ') {
                currentToken += input[i];
            }
            currentToken.trim(); // Remove leading/trailing whitespace
            if (currentToken.length() > 0) {
                Command cmd = parseToken(currentToken); // Parse the token
                // If the command is valid, add it to the queue
                if (cmd.type != CMD_INVALID) {
                     if (queueCount < QUEUE_SIZE) { // Double-check space (safety)
                        cmdQueue[queueRear] = cmd; // Add command to the rear
                        queueRear = (queueRear + 1) % QUEUE_SIZE; // Move rear pointer (circular)
                        queueCount++; // Increment command count
                        cmdAddedCount++;
                    } else {
                         // This should not happen if pre-check worked, but log error if it does
                         Serial.println("ERROR: Queue full during enqueue - Pre-check failed?");
                         break; // Stop processing this string if queue is unexpectedly full
                    }
                }
            }
            currentToken = ""; // Reset for the next token
        } else {
            currentToken += input[i]; // Build the token
        }
    }
     // Report how many commands were successfully added
     if (cmdAddedCount > 0) {
        Serial.print(cmdAddedCount);
        Serial.println(" command(s) successfully queued.");
    }
}


#ifdef WEB_MODE
// ==========================================================
// --- Web Server Handlers ---
// ==========================================================

// Handles requests to the root URL ("/") - displays the control form
void handleRoot() {
  // Simple HTML form (Restored full version)
  String html = R"(
  <!DOCTYPE html><html><head><title>ESP32 Control</title>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <style>
    body { font-family: sans-serif; padding: 15px; }
    h1, h2 { text-align: center; }
    label { display: block; margin-top: 10px; font-weight: bold; }
    input[type='text'] { width: calc(100% - 22px); padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; }
    button { display: block; width: 100%; background-color: #4CAF50; color: white; padding: 14px 20px; margin-top: 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
    button:hover { background-color: #45a049; }
    pre { background-color: #f4f4f4; border: 1px solid #ddd; padding: 10px; white-space: pre-wrap; word-wrap: break-word; margin-top: 15px; min-height: 100px; }
    .status-container { margin-top: 20px; }
  </style>
  </head><body>
  <h1>ESP32 Device Control</h1>
  <form action='/command' method='POST' id='commandForm'>
    <label for='cmd'>Command String:</label>
    <input type='text' id='cmd' name='cmd' size='50' placeholder='e.g., R-1000 G-0.5 P-50-2.0 H-75 S-A-5 D-1000'>
    <button type='submit'>Send Command</button>
  </form>

  <div class='status-container'>
    <h2>Live Status</h2>
    <pre id='status'>Loading status...</pre>
  </div>

  <script>
    // Function to fetch and update status
    function updateStatus() {
      fetch('/status')
        .then(response => {
          if (!response.ok) { throw new Error('Network response was not ok'); }
          return response.text();
        })
        .then(text => {
          document.getElementById('status').textContent = text;
        })
        .catch(error => {
          console.error('Error fetching status:', error);
          document.getElementById('status').textContent = 'Error fetching status. Check connection/server.';
        });
    }

    // Update status every 2 seconds
    setInterval(updateStatus, 2000);

    // Initial status load on page load
    document.addEventListener('DOMContentLoaded', updateStatus);

    // Optional: Clear input after submission?
    // document.getElementById('commandForm').addEventListener('submit', function() {
    //   setTimeout(() => { this.reset(); }, 100); // Short delay before reset
    // });
  </script>
  </body></html>)";
  server.send(200, "text/html", html);
}

// Handles POST requests to "/command" - receives and processes command strings
void handleCommand() {
  // Check if the 'cmd' argument exists in the POST request
  if (!server.hasArg("cmd")) {
    server.send(400, "text/plain", "Bad Request: Missing 'cmd' argument.");
    return;
  }
  String input = server.arg("cmd"); // Get the command string
  input.trim(); // Remove leading/trailing whitespace
  Serial.println("Received Web Command: " + input); // Log received command

  if (input.length() == 0) {
      server.send(400, "text/plain", "Bad Request: Empty command string.");
      return;
  }

  // --- Queue Pre-Check: Ensure enough space before processing ---
  int requiredSlots = countValidCommandsInString(input); // Count how many valid commands are in the string
  int availableSlots = QUEUE_SIZE - queueCount;         // Calculate available space

  if (requiredSlots == 0) {
       server.send(400, "text/plain", "No valid commands found in the input string.");
       Serial.println("Web command rejected: No valid commands found.");
  } else if (requiredSlots > availableSlots) {
      // Not enough space in the queue
      String msg = "Queue full. Required: " + String(requiredSlots) +
                   ", Available: " + String(availableSlots) + ". Command rejected.";
      server.send(503, "text/plain", msg); // 503 Service Unavailable (Queue Full)
      Serial.println(msg);
  } else {
      // --- Enqueue Commands: Space is available ---
      processAndEnqueueCommands(input); // Parse again and add valid commands to queue
      String msg = String(requiredSlots) + " command(s) accepted. Queue: " +
                   String(queueCount) + "/" + String(QUEUE_SIZE);
      server.send(200, "text/plain", msg); // Send success response
      // Serial printing already happens in processAndEnqueueCommands
  }
}

// Handles GET requests to "/status" - provides current machine status
void handleStatus() {
  String status = "--- VESC Status ---\n";
  // VESC1 = Grinder (Duty), VESC2 = Drum (RPM)
  status += "Grinder (Duty): Target=" + String(targetDuty1, 3) + ", Current=" + String(currentDuty1, 3) + "\n";
  status += "Drum (RPM): Target=" + String(targetRpm2) + ", Current=" + String(currentRpm2, 0) + "\n";
  status += "--- Water Pump Status ---\n";
  status += "State: " + String(dispensingActive ? "DISPENSING" : "IDLE") + "\n";
  status += "Target: " + String(targetVolumeML, 1) + " mL @ " + String(targetFlowRateMLPS, 2) + " mL/s\n";
  status += "Current: " + String(dispensedVolumeML, 1) + " mL / " + String(currentFlowRateMLPS, 2) + " mL/s\n";
  noInterrupts(); // Read volatile pulseCount safely
  status += "Pulses: " + String(pulseCount) + "\n";
  interrupts();
  status += "--- Heater Status ---\n";
  status += "State: " + String(heaterActive ? "ON" : "OFF") + "\n";
  status += "--- Servo Status ---\n";
  ServoControlState* states[] = {&servoAState, &servoBState, &servoCState, &servoDState};
  unsigned long now = millis();
  for (int i = 0; i < 4; ++i) {
      status += String(states[i]->id) + ": ";
      if (states[i]->isRunning) {
          status += String(states[i]->isForward ? "FWD" : "REV");
          status += " (Speed " + String(states[i]->isForward ? states[i]->forwardSpeed : states[i]->reverseSpeed) + ")";
          // Calculate remaining time safely (prevent underflow)
          unsigned long remaining_ms = (states[i]->stopTime > now) ? (states[i]->stopTime - now) : 0;
          status += " Rem: " + String(remaining_ms / 1000.0, 1) + "s"; // Show one decimal place
      } else {
          status += "STOPPED (Speed " + String(SERVO_STOP_SPEED) + ")";
      }
      status += " | ";
  }
  // Remove trailing " | "
  if (status.endsWith(" | ")) { status = status.substring(0, status.length() - 3); }
  status += "\n--- System Status ---\n";
  status += "Command Queue: " + String(queueCount) + "/" + String(QUEUE_SIZE) + "\n";
  status += "Delay Active: " + String(millis() < generalDelayEndTime ? "YES (" + String((generalDelayEndTime - millis())/1000.0, 1) + "s left)" : "NO") + "\n";
  status += "Uptime: " + String(millis() / 1000) + " s\n"; // Add uptime

  server.send(200, "text/plain", status); // Send the status text
}

// Handles requests to URLs not matching defined routes
void handleNotFound() {
  server.send(404, "text/plain", "Not Found.");
}
#endif // WEB_MODE

// ==========================================================
// --- Core Logic Functions ---
// ==========================================================

// Helper to get the character for the command type (for printing)
char getCommandTypeChar(CommandType type) {
    switch (type) {
        case CMD_R: return 'R'; case CMD_G: return 'G'; case CMD_P: return 'P';
        case CMD_H: return 'H'; case CMD_S: return 'S'; case CMD_D: return 'D';
        default: return '?';
    }
}

// Executes the next command from the queue if available and no delay is active
void executeCommandFromQueue() {
  // Check if queue has commands and the general delay timer has passed
  if (queueCount > 0 && millis() >= generalDelayEndTime) {
    // Get command from the front of the queue
    Command cmd = cmdQueue[queueFront];
    // Advance the front pointer (circularly)
    queueFront = (queueFront + 1) % QUEUE_SIZE;
    // Decrement the count of commands in the queue
    queueCount--;

    // Print indication that a command is being executed
    Serial.print("Executing Cmd: ");
    Serial.print(getCommandTypeChar(cmd.type)); // Print command letter (R, G, P...)
    Serial.print("-"); // Print separator

    // Execute based on command type
    switch (cmd.type) {
      case CMD_R: // Set Drum Target RPM (VESC2)
        Serial.println(String(cmd.value1));
        targetRpm2 = cmd.value1; // Update target RPM
        // Ramping happens continuously in updateVescControl()
        break;

      case CMD_G: // Set Grinder Target Duty (VESC1)
        Serial.println(String(cmd.value1, 3));
        targetDuty1 = constrain(cmd.value1, -1.0f, 1.0f); // Update target duty, constrained
        // Ramping happens continuously in updateVescControl()
        break;

      case CMD_P: // Start Water Dispensing
        Serial.println(String(cmd.value1, 1) + "-" + String(cmd.value2, 2));
        // Prevent starting if already running
        if (!dispensingActive) {
          targetVolumeML = cmd.value1;     // Set target volume
          targetFlowRateMLPS = cmd.value2; // Set target flow rate

          // Reset pump state variables for the new dispense cycle
          dispensedVolumeML = 0.0;
          noInterrupts(); // Safely reset volatile pulseCount
          pulseCount = 0;
          interrupts();
          lastPulseCount = 0;      // Reset for delta calculation
          lastPulsePrintTime = 0;  // Reset print timer
          currentFlowRateMLPS = 0.0; // Reset current rate calculation
          // Reset PID terms
          pidError = 0.0; lastError = 0.0; integralError = 0.0; derivativeError = 0.0; pidOutput = 0.0;
          // Calculate initial feedforward duty based on target rate
          feedforwardDuty = calculateFeedforwardDuty(targetFlowRateMLPS);

          // Record start time and reset timers
          dispenseStartTime = millis();
          lastFlowCalcTime = dispenseStartTime;
          lastControlTime = dispenseStartTime;

          dispensingActive = true;       // Set flag that pump is active
          pumpUsedSinceHeaterOn = true; // Mark pump as used (for heater safety timeout)

          Serial.print("  Starting dispense. Target: "); Serial.print(targetVolumeML);
          Serial.print("mL @ "); Serial.print(targetFlowRateMLPS);
          Serial.print("mL/s. FF Duty: "); Serial.println(feedforwardDuty);
          // Apply initial duty cycle (mostly feedforward)
          ledcWrite(PUMP_LEDC_CHANNEL, feedforwardDuty);
        } else {
          // Pump is already running, log a warning
          Serial.println("  Warning: Cannot start pump, already dispensing.");
        }
        break;

      case CMD_H: // Set Heater Power
      { // Use block scope
        Serial.println(String(cmd.value1)); // Print target power %
        // Map power percentage (0-100) to PWM duty cycle (0-255)
        int heaterDuty = map(constrain((int)cmd.value1, 0, 100), 0, 100, 0, 255);
        ledcWrite(HEATER_LEDC_CHANNEL, heaterDuty); // Set heater PWM
        heaterActive = (heaterDuty > 0); // Update heater active flag
        if (heaterActive) {
          heaterStartTime = millis();      // Record time heater was turned on
          pumpUsedSinceHeaterOn = false; // Reset pump usage flag for timeout check
          Serial.println("  Heater ON");
        } else {
           Serial.println("  Heater OFF");
        }
        break;
      }
      case CMD_S: // Start Servo Periodic Movement
        { // Block scope
            float durationSeconds = cmd.value1; // Duration comes from parsed command value1
            unsigned long durationMillis = (unsigned long)(durationSeconds * 1000.0f); // Convert to ms
            unsigned long currentTime = millis(); // Get current time
            ServoControlState* stateToUpdate = nullptr; // Pointer to the state struct to modify

            // Print details
            Serial.print(cmd.id); // S-ID
            Serial.print("-");
            Serial.println(String(durationSeconds, 1) + "s"); // S-ID-Duration

            // Find the correct servo state struct based on the ID
            switch (cmd.id) {
                case 'A': stateToUpdate = &servoAState; break;
                case 'B': stateToUpdate = &servoBState; break;
                case 'C': stateToUpdate = &servoCState; break;
                case 'D': stateToUpdate = &servoDState; break;
                default:
                    Serial.println("  Error: Invalid Servo ID in command queue!"); // Should have been caught by parser
                    break;
            }

            // If a valid state struct was found, start the servo sequence
            if (stateToUpdate != nullptr) {
                stateToUpdate->isRunning = true;                         // Mark servo as running
                stateToUpdate->stopTime = currentTime + durationMillis;  // Calculate when it should stop
                stateToUpdate->periodStartTime = currentTime;            // Start the first period now
                stateToUpdate->isForward = true;                         // Always start moving forward
                stateToUpdate->servoObject.write(stateToUpdate->forwardSpeed); // Command initial speed

                // Log the start action
                Serial.print("  Servo "); Serial.print(cmd.id);
                Serial.print(" starting periodic run for "); Serial.print(durationSeconds, 1); Serial.println("s");
                Serial.print("    -> Starting FORWARD (Speed: "); Serial.print(stateToUpdate->forwardSpeed); Serial.println(")");
            }
        }
        break;

      case CMD_D: // Start General Delay
        Serial.println(String(cmd.value1, 0) + "ms"); // Print delay duration
        generalDelayEndTime = millis() + (unsigned long)cmd.value1; // Set time when delay ends
        Serial.println("  Delaying execution...");
        break;

      default: // Should not happen if parseToken works correctly
        Serial.println(" ERROR: Executing invalid command type from queue!");
        break;
    }
  }
}

// Manages the water pump state, flow calculation, and PID control when active
void updateWaterPump() {
  // Only run logic if the pump dispensing sequence is active
  if (!dispensingActive) return;

  unsigned long currentTime = millis(); // Get current time once for this function call

  // --- Periodic Pulse Count Printing ---
  // Print the raw pulse count at regular intervals for debugging/monitoring
  if (currentTime - lastPulsePrintTime >= PULSE_PRINT_INTERVAL) {
      noInterrupts(); // Safely read the volatile pulseCount variable
      unsigned long currentPulses = pulseCount;
      interrupts();

      //Serial.print("Pump Active - Ticks: "); // Print status message
      //Serial.println(currentPulses);         // Print the count

      lastPulsePrintTime = currentTime; // Reset the timer for the next print interval
  }

  // --- Flow Rate Calculation Task ---
  // Calculate flow rate based on pulses counted over the interval
  if (currentTime - lastFlowCalcTime >= flowCalcInterval) {
    noInterrupts(); // Safely read volatile pulseCount
    unsigned long currentPulses = pulseCount;
    interrupts();

    unsigned long deltaPulses = currentPulses - lastPulseCount; // Pulses since last calculation
    float deltaTimeSeconds = (currentTime - lastFlowCalcTime) / 1000.0; // Time elapsed in seconds
    lastFlowCalcTime = currentTime; // Update time for next interval
    lastPulseCount = currentPulses; // Update count for next interval's delta

    // Calculate rate if time has passed
    if (deltaTimeSeconds > 0.001) { // Avoid division by zero on very fast loops
        float pps = (float)deltaPulses / deltaTimeSeconds; // Pulses per second
        // Estimate Ticks/mL based on current/target flow rate for conversion
        float ticksPerML_est = getTicksPerML(currentFlowRateMLPS > 0.05 ? currentFlowRateMLPS : targetFlowRateMLPS);
        // Calculate flow rate in mL/s
        if (ticksPerML_est > 0.1) {
            currentFlowRateMLPS = pps / ticksPerML_est;
            // Update total dispensed volume using this interval's data
            dispensedVolumeML += (float)deltaPulses / ticksPerML_est;
        } else {
            currentFlowRateMLPS = 0.0; // Assume zero flow if ticks/mL is invalid
        }
    }
    // else: Very short interval, skip calculation this cycle
  }

  // --- PID Control Task ---
  // Adjust pump PWM duty cycle to maintain target flow rate
  if (currentTime - lastControlTime >= controlInterval) {
      float dt = (currentTime - lastControlTime) / 1000.0; // Delta time in seconds
      lastControlTime = currentTime; // Update time for next interval

      if (dt > 0.001) { // Avoid division by zero
          // --- Calculate PID terms ---
          pidError = targetFlowRateMLPS - currentFlowRateMLPS; // Error = Target - Actual
          integralError += pidError * dt;                      // Accumulate integral term
          integralError = constrain(integralError, -maxIntegral, maxIntegral); // Apply anti-windup
          derivativeError = (pidError - lastError) / dt;       // Calculate derivative term
          pidOutput = (kp * pidError) + (ki * integralError) + (kd * derivativeError); // Calculate total PID output

          lastError = pidError; // Store current error for next derivative calculation

          // --- Combine Feedforward and PID ---
          // Feedforward provides baseline duty, PID provides correction
          int totalDuty = calculateFeedforwardDuty(targetFlowRateMLPS) + (int)round(pidOutput);

          // --- Constrain total duty cycle to valid PWM range (0-255) ---
          totalDuty = constrain(totalDuty, 0, 255);

          // --- Apply control signal to pump ---
          ledcWrite(PUMP_LEDC_CHANNEL, totalDuty);

          // --- Optional: Print PID status for tuning ---
          // Serial.print("PID: Err="); Serial.print(pidError, 2); Serial.print(" Int="); Serial.print(integralError, 2);
          // Serial.print(" Der="); Serial.print(derivativeError, 2); Serial.print(" Out="); Serial.print(pidOutput, 2);
          // Serial.print(" FF="); Serial.print(feedforwardDuty); Serial.print(" TotalDuty="); Serial.println(totalDuty);
      }
  }

  // --- Check Stop Condition ---
  // Stop dispensing if the target volume has been reached
  if (dispensedVolumeML >= targetVolumeML) {
    ledcWrite(PUMP_LEDC_CHANNEL, 0); // Stop the pump PWM
    dispensingActive = false;       // Update state flag
    unsigned long duration = millis() - dispenseStartTime; // Calculate total duration

    // Print summary of the completed dispense operation
    Serial.println("\n--- Dispense Complete ---");
    Serial.print("Target Vol: "); Serial.print(targetVolumeML, 1); Serial.println(" mL");
    Serial.print("Actual Vol: "); Serial.print(dispensedVolumeML, 1); Serial.println(" mL");
    Serial.print("Target Rate: "); Serial.print(targetFlowRateMLPS, 2); Serial.println(" mL/s");
    // Calculate and print average flow rate
    if (duration > 0) {
        float avgFlowRate = (dispensedVolumeML / ((float)duration / 1000.0));
        Serial.print("Average Rate: "); Serial.print(avgFlowRate, 2); Serial.println(" mL/s");
    }
    Serial.print("Duration: "); Serial.print(duration); Serial.println(" ms");
    noInterrupts(); // Safely read final pulse count
    Serial.print("Final Pulse Count: "); Serial.println(pulseCount);
    interrupts();
    Serial.println("-------------------------");

    // If heater was active, potentially start cooldown delay
    if (heaterActive) {
        generalDelayEndTime = millis() + POST_PUMP_COOLDOWN; // Start post-pump heater cooldown delay
        Serial.println("Heater cooldown started (" + String(POST_PUMP_COOLDOWN) + "ms)");
    }
  }
}

// Updates VESC control signals based on ramping logic
// VESC1=Grinder/Duty, VESC2=Drum/RPM
void updateVescControl() {
  uint32_t now_us = micros(); // Use microseconds for finer control interval

  // Step VESC1 (Grinder Duty) if interval passed
  if ((now_us - lastDutyStepTime) >= DUTY_STEP_INTERVAL_US) {
    stepDuty1();                  // Calculate next duty step
    vesc1.setDuty(currentDuty1); // Send updated Duty command to VESC1
    lastDutyStepTime = now_us;    // Reset timer
  }

  // Step VESC2 (Drum RPM) if interval passed
  if ((now_us - lastRpmStepTime) >= RPM_STEP_INTERVAL_US) {
    stepRpm2();                       // Calculate next RPM step
    vesc2.setRPM((int32_t)currentRpm2); // Send updated RPM command to VESC2
    lastRpmStepTime = now_us;         // Reset timer
  }
}

// Updates the state of a single servo (periodic motion, stopping)
void updateServo(ServoControlState& state) {
  // Only run if the servo was commanded to run
  if (!state.isRunning) return;

  unsigned long currentTime = millis(); // Get current time

  // --- Check 1: Has the total run time expired? ---
  if (currentTime >= state.stopTime) {
    state.servoObject.write(SERVO_STOP_SPEED); // Stop the servo
    state.isRunning = false;                   // Mark as not running
    Serial.print("Servo "); Serial.print(state.id);
    Serial.println(" stopped (Total time elapsed). Speed: " + String(SERVO_STOP_SPEED));
    return; // Finished with this servo
  }

  // --- Check 2: Handle periodic forward/reverse motion ---
  unsigned long timeInPeriod = currentTime - state.periodStartTime; // Time elapsed in current period

  if (state.isForward) {
    // Currently moving forward, check if it's time to switch to reverse
    if (timeInPeriod >= FORWARD_DURATION_MS) {
      state.servoObject.write(state.reverseSpeed); // Switch to reverse speed
      state.isForward = false;                     // Update direction flag
      // Log the direction change
      Serial.print("Servo "); Serial.print(state.id);
      Serial.print(" switching to REVERSE (Speed: "); Serial.print(state.reverseSpeed); Serial.println(")");
      // Don't reset periodStartTime here, we are still within the same period cycle
    }
  } else { // Currently moving reverse
    // Check if the full period duration is complete
    if (timeInPeriod >= SERVO_PERIOD_MS) {
      state.servoObject.write(state.forwardSpeed); // Switch back to forward speed
      state.isForward = true;                      // Update direction flag
      state.periodStartTime = currentTime;         // Start the *next* period cycle now
      // Log the direction change
       Serial.print("Servo "); Serial.print(state.id);
       Serial.print(" switching to FORWARD (Speed: "); Serial.print(state.forwardSpeed); Serial.println(")");
    }
  }
}


// Checks for safety conditions (heater timeout, post-pump cooldown)
void checkSafetyFeatures() {
    unsigned long currentTime = millis();

    // 1. Heater Timeout: Turn off heater if it's been on too long without pump usage
    if (heaterActive && !pumpUsedSinceHeaterOn && (currentTime - heaterStartTime > HEATER_TIMEOUT)) {
        Serial.println("Safety Trigger: Heater timed out (pump not used). Turning OFF.");
        ledcWrite(HEATER_LEDC_CHANNEL, 0); // Turn off heater PWM
        heaterActive = false;              // Update state flag
    }

    // 2. Heater Cooldown after Pump: Turn off heater after post-pump delay, only if pump is NOT running
    // This relies on generalDelayEndTime being set correctly when the pump finishes.
    if (!dispensingActive && heaterActive && generalDelayEndTime > 0 && currentTime >= generalDelayEndTime) {
        // Check if the delay end time is plausibly the post-pump cooldown end time
        // Calculate roughly when the pump actually stopped
        unsigned long actualPumpStopTime = dispenseStartTime + (unsigned long)((dispensedVolumeML / (targetFlowRateMLPS > 0 ? targetFlowRateMLPS : 1.0)) * 1000.0);
        // Check if the general delay ended shortly after the pump stopped + cooldown period
        // Add a small buffer (e.g., 200ms) for timing variations
        if (generalDelayEndTime > actualPumpStopTime && generalDelayEndTime < (actualPumpStopTime + POST_PUMP_COOLDOWN + 200) ) {
           Serial.println("Heater post-pump cooldown finished. Turning OFF.");
           ledcWrite(HEATER_LEDC_CHANNEL, 0); // Turn off heater PWM
           heaterActive = false;              // Update state flag
        }
        // Note: generalDelayEndTime doesn't need explicit reset; time just passes it.
    }

    // Note: The no-flow safety check from a previous version was removed as per code state.
    // If needed, it would be added here.
}


// ==========================================================
// --- ESP32 Setup ---
// ==========================================================
void setup() {
  Serial.begin(SERIAL_BAUD);
  // Wait up to 2 seconds for Serial Monitor to connect (optional)
  while (!Serial && millis() < 2000);
  Serial.println("\n\n--- Combined Control System Initializing ---");

  // --- Logic Level Shifter Enable ---
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH); // Enable the shifter (Active HIGH assumed)
  Serial.println("Logic Level Shifter Enabled (Pin " + String(OE_PIN) + ")");

  // --- VESC Setup (VESC1=Grinder/Duty, VESC2=Drum/RPM) ---
  Serial1.begin(SERIAL_BAUD, SERIAL_8N1, VESC1_RX_PIN, VESC1_TX_PIN); // Grinder VESC UART
  Serial2.begin(SERIAL_BAUD, SERIAL_8N1, VESC2_RX_PIN, VESC2_TX_PIN); // Drum VESC UART
  vesc1.setSerialPort(&Serial1); // Assign Serial1 to vesc1 object
  vesc2.setSerialPort(&Serial2); // Assign Serial2 to vesc2 object
  Serial.println("VESC UART Ports Initialized (VESC1=Grinder, VESC2=Drum).");

  // --- Water Pump Setup ---
  pinMode(PUMP_PWM_PIN, OUTPUT);
  // Setup LEDC PWM channel for the pump (using PUMP_LEDC_CHANNEL = 4)
  ledcSetup(PUMP_LEDC_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(PUMP_PWM_PIN, PUMP_LEDC_CHANNEL); // Attach pin to channel
  ledcWrite(PUMP_LEDC_CHANNEL, 0); // Ensure pump is off initially
  // Setup flow sensor pin and interrupt
  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP); // Use pullup if sensor is open-collector/drain
  attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), flowISR, RISING); // Attach ISR
  Serial.println("Water Pump & Flow Sensor Initialized.");

  // --- Heater Setup ---
  pinMode(HEATER_PIN, OUTPUT);
  // Setup LEDC PWM channel for the heater (using HEATER_LEDC_CHANNEL = 5)
  ledcSetup(HEATER_LEDC_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(HEATER_PIN, HEATER_LEDC_CHANNEL); // Attach pin to channel
  ledcWrite(HEATER_LEDC_CHANNEL, 0); // Ensure heater is off initially
  Serial.println("Heater Initialized.");

  // --- Servo Setup ---
  ESP32PWM::allocateTimer(0); // Allocate timers needed by ESP32Servo library
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  servoA.attach(SERVO_PIN_A); // Attach servo objects to pins
  servoB.attach(SERVO_PIN_B);
  servoC.attach(SERVO_PIN_C);
  servoD.attach(SERVO_PIN_D);
  servoA.write(SERVO_STOP_SPEED); // Set initial stopped position
  servoB.write(SERVO_STOP_SPEED);
  servoC.write(SERVO_STOP_SPEED);
  servoD.write(SERVO_STOP_SPEED);
  Serial.println("Servos Initialized & Stopped (Speed: " + String(SERVO_STOP_SPEED) + ").");

#ifdef WEB_MODE
  // --- WiFi & Web Server Setup ---
  Serial.print("Connecting to WiFi: "); Serial.println(ssid);
  WiFi.begin(ssid, password);
  int wifi_retries = 0;
  // Wait for connection (with timeout)
  while (WiFi.status() != WL_CONNECTED && wifi_retries < 20) {
    delay(500); Serial.print("."); wifi_retries++;
   }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected!");
    Serial.print("IP Address: "); Serial.println(WiFi.localIP());
    /* // Optional mDNS setup - Add #include <ESPmDNS.h> and MDNS.update() in loop
    if (MDNS.begin("esp32-control")) { // Set hostname for mDNS (e.g., http://esp32-control.local)
      Serial.println("mDNS responder started (esp32-control.local)");
       MDNS.addService("http", "tcp", 80); // Announce web server service
    } else { Serial.println("Error setting up mDNS responder!"); }
    */
    // Define web server routes
    server.on("/", HTTP_GET, handleRoot);          // Serve the main HTML page
    server.on("/command", HTTP_POST, handleCommand); // Handle command submissions
    server.on("/status", HTTP_GET, handleStatus);    // Provide status updates
    server.onNotFound(handleNotFound);             // Handle invalid URLs
    server.begin();                                // Start the web server
    Serial.println("Web Server Started.");
  } else {
    Serial.println("\nWiFi Connection Failed!");
    // Consider fallback action? (e.g., restart, enter error state)
  }
#endif // WEB_MODE

  // --- Print Ready Message and Command Help ---
  Serial.println("\n--- System Ready ---");
  Serial.println("Enter commands via Serial Monitor or Web Interface (if enabled).");
  Serial.println("Format examples:");
  Serial.println("  R-<rpm>           (Drum RPM, e.g., R-3000)");
  Serial.println("  G-<duty>          (Grinder Duty -1.0 to 1.0, e.g., G-0.75)");
  Serial.println("  P-<vol>-<rate>    (Pump Volume[mL] & Rate[mL/s], e.g., P-100-2.5)");
  Serial.println("  H-<power%>        (Heater Power 0-100%, e.g., H-80)");
  Serial.println("  S-<id>-<time_sec> (Servo ID [A-D] run duration, e.g., S-A-5)");
  Serial.println("                    (Period: " + String(SERVO_PERIOD_SECONDS) + "s, " + String(FORWARD_DUTY_CYCLE * 100, 0) + "% Fwd / " + String(REVERSE_DUTY_CYCLE * 100, 0) + "% Rev)");
  Serial.println("  D-<ms>            (Delay execution [milliseconds], e.g., D-2000)");
  Serial.println("Combine multiple commands with spaces.");
  Serial.println("--------------------");
}

// ==========================================================
// --- Arduino Loop ---
// ==========================================================
void loop() {

#ifdef WEB_MODE
  server.handleClient(); // Handle incoming web client requests
  // MDNS.update(); // Call if using mDNS
#endif // WEB_MODE

// Process Serial Input only if SERIAL_MODE is defined OR if WEB_MODE is disabled
#if defined(SERIAL_MODE) || !defined(WEB_MODE)
  // Handle Serial Input (non-blocking)
  while (Serial.available() > 0) {
    char c = Serial.read();
    // Check for end-of-line characters
    if (c == '\n' || c == '\r') {
      serialInputBuffer.trim(); // Remove whitespace from received line
      if (serialInputBuffer.length() > 0) {
        Serial.println("Received Serial Command: " + serialInputBuffer);
        // Pre-check queue space before processing
        int requiredSlots = countValidCommandsInString(serialInputBuffer);
        int availableSlots = QUEUE_SIZE - queueCount;
        if (requiredSlots == 0) {
             Serial.println("No valid commands found in the input string.");
        } else if (requiredSlots > availableSlots) {
            // Not enough space
            Serial.println("Queue full. Required: " + String(requiredSlots) +
                         ", Available: " + String(availableSlots) + ". Command rejected.");
        } else {
            // Space available, process and enqueue
            processAndEnqueueCommands(serialInputBuffer);
        }
      }
      serialInputBuffer = ""; // Clear buffer for next command line
    } else if (isprint(c) && serialInputBuffer.length() < 200) {
      // Add printable characters to the buffer (with size limit)
      serialInputBuffer += c;
    }
  }
#endif // SERIAL_MODE check

  // --- Continuous Operations ---
  // These functions handle ongoing tasks like ramping motors, controlling pump PID,
  // managing servo movements, etc. They should be non-blocking.
  updateVescControl();      // Update VESC ramping and send commands
  updateWaterPump();        // Update pump PID control and volume check if active
  // Update ALL Servo States (handles periodic motion and stopping)
  updateServo(servoAState);
  updateServo(servoBState);
  updateServo(servoCState);
  updateServo(servoDState);

  // --- Command Queue Execution ---
  executeCommandFromQueue(); // Process one command from the queue if ready and no delay

  // --- Safety Checks ---
  checkSafetyFeatures();    // Check heater timeouts etc.

  // Yield allows background tasks (like WiFi, background OS tasks) to run - Important!
  yield();
}
