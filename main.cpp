#include <Arduino.h>
#include <math.h>       // For pow() in pump control
#include <ESP32Servo.h> // For servos
#include "VescUart.h"   // For VESC control
#include <ctype.h>      // For toupper()

// --- Operation Mode ---
#define WEB_MODE      // Uncomment for Web Server control
// #define SERIAL_MODE // Uncomment for Serial Monitor control (Can be active alongside WEB_MODE)

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
// VESC1 = Grinder (Current Control), VESC2 = Drum (RPM Control)
const int VESC1_RX_PIN = 12; // Serial1 RX for GRINDER Motor VESC (Current)
const int VESC1_TX_PIN = 13; // Serial1 TX for GRINDER Motor VESC (Current)
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

// VESC Configuration (VESC1=Grinder/Current, VESC2=Drum/RPM)
// Note: Ramping for current control is removed, target current is sent periodically.
// Duty settings are now only relevant for VESC1 command sending frequency.
#define CURRENT_SEND_INTERVAL_US 500UL // How often to send target current (micros) - Was DUTY_STEP_INTERVAL_US
#define RPM_STEP_SIZE            7.0f   // Drum motor (VESC2) RPM step
#define RPM_STEP_INTERVAL_US     100UL  // Drum motor (VESC2) step interval (micros)


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
#define NO_FLOW_TIMEOUT 2000    // Heater auto-off if no flow detected for this duration (ms) <-- NEW
#define POST_PUMP_COOLDOWN 1000 // Heater off delay after pump stops (ms)
#define QUEUE_SIZE 20           // Command queue capacity

// ==========================================================
// --- Global Variables & Objects ---
// ==========================================================

// VESC Objects and State (VESC1=Grinder/Current, VESC2=Drum/RPM)
VescUart vesc1; // Grinder Motor (Current Control)
VescUart vesc2; // Drum Motor (RPM Control)
float targetCurrent1 = 0.0f; // Target Current for VESC1 (Grinder) in Amps <-- CHANGED
float currentRpm2 = 0.0f; // Current RPM for VESC2 (Drum) - used for ramping
float targetRpm2  = 0.0f; // Target RPM for VESC2 (Drum)
uint32_t lastCurrentSendTime = 0; // Timer for VESC1 current sending <-- RENAMED from lastDutyStepTime
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

// --- State for No-Flow Safety Check --- <-- NEW
unsigned long lastPulseCheckCount = 0; // Stores pulseCount during previous safety check
unsigned long lastNoPulseTime = 0;     // Stores millis() when heater was ON but no flow started

// Command structure and queue definitions
enum CommandType { CMD_R, CMD_G, CMD_P, CMD_H, CMD_S, CMD_D, CMD_INVALID }; // R=Drum RPM, G=Grinder Current
struct Command {
  CommandType type;
  float value1 = 0; // R:RPM, G:Amps, P:Volume, H:Power%, S:Duration(sec), D:Delay(ms) <-- G changed
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

// --- VESC Ramping Helper (VESC2=Drum/RPM Only) --- <-- REMOVED stepDuty1
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
    case 'G': // G-<amps> (Grinder Current) <-- CHANGED
      cmd.type = CMD_G;
      cmd.value1 = params.toFloat();
      // Validate current range (0 to 2 Amps)
      if (cmd.value1 < 0.0 || cmd.value1 > 2.0) {
         Serial.println("Warning: Grinder Current " + String(cmd.value1) + " Amps out of range (0.0 to 2.0). Clamping will occur.");
         // Value will be clamped during execution
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
int countValidCommandsInString(const String& input) {
    String currentToken; int validCount = 0;
    for (int i = 0; i < input.length(); i++) {
        if (input[i] == ' ' || i == input.length() - 1) {
            if (i == input.length() - 1 && input[i] != ' ') currentToken += input[i];
            currentToken.trim(); if (currentToken.length() > 0) { if (parseToken(currentToken).type != CMD_INVALID) validCount++; } currentToken = "";
        } else { currentToken += input[i]; }
    } return validCount;
}

// Parses a command string and adds *valid* commands to the queue.
void processAndEnqueueCommands(const String& input) {
    String currentToken; int cmdAddedCount = 0;
    for (int i = 0; i < input.length(); i++) {
        if (input[i] == ' ' || i == input.length() - 1) {
            if (i == input.length() - 1 && input[i] != ' ') currentToken += input[i];
            currentToken.trim(); if (currentToken.length() > 0) { Command cmd = parseToken(currentToken); if (cmd.type != CMD_INVALID) { if (queueCount < QUEUE_SIZE) { cmdQueue[queueRear] = cmd; queueRear = (queueRear + 1) % QUEUE_SIZE; queueCount++; cmdAddedCount++; } else { Serial.println("ERROR: Queue full during enqueue."); break; } } } currentToken = "";
        } else { currentToken += input[i]; }
    } if (cmdAddedCount > 0) { Serial.print(cmdAddedCount); Serial.println(" command(s) successfully queued."); }
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
    <input type='text' id='cmd' name='cmd' size='50' placeholder='e.g., R-1000 G-1.5 P-50-2.0 H-75 S-A-5 D-1000'> <button type='submit'>Send Command</button>
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
  </script>
  </body></html>)";
  server.send(200, "text/html", html);
}

// Handles POST requests to "/command" - receives and processes command strings
void handleCommand() {
  if (!server.hasArg("cmd")) { server.send(400, "text/plain", "Bad Request: Missing 'cmd'."); return; }
  String input = server.arg("cmd"); input.trim(); Serial.println("Received Web Command: " + input);
  if (input.length() == 0) { server.send(400, "text/plain", "Bad Request: Empty command."); return; }
  int requiredSlots = countValidCommandsInString(input); int availableSlots = QUEUE_SIZE - queueCount;
  if (requiredSlots == 0) { server.send(400, "text/plain", "No valid commands found."); Serial.println("Web command rejected: No valid commands."); }
  else if (requiredSlots > availableSlots) { String msg = "Queue full. Required: " + String(requiredSlots) + ", Available: " + String(availableSlots); server.send(503, "text/plain", msg); Serial.println(msg); }
  else { processAndEnqueueCommands(input); String msg = String(requiredSlots) + " command(s) accepted. Queue: " + String(queueCount) + "/" + String(QUEUE_SIZE); server.send(200, "text/plain", msg); }
}

// Handles GET requests to "/status" - provides current machine status
void handleStatus() {
  String status = "--- VESC Status ---\n";
  // VESC1 = Grinder (Current), VESC2 = Drum (RPM)
  status += "Grinder (Amps): Target=" + String(targetCurrent1, 2) + " A\n"; // <-- CHANGED to show target current
  status += "Drum (RPM): Target=" + String(targetRpm2) + ", Current=" + String(currentRpm2, 0) + "\n";
  status += "--- Water Pump Status ---\n";
  status += "State: " + String(dispensingActive ? "DISPENSING" : "IDLE") + "\n";
  status += "Target: " + String(targetVolumeML, 1) + " mL @ " + String(targetFlowRateMLPS, 2) + " mL/s\n";
  status += "Current: " + String(dispensedVolumeML, 1) + " mL / " + String(currentFlowRateMLPS, 2) + " mL/s\n";
  noInterrupts(); status += "Pulses: " + String(pulseCount) + "\n"; interrupts();
  status += "--- Heater Status ---\n";
  status += "State: " + String(heaterActive ? "ON" : "OFF") + "\n";
  status += "--- Servo Status ---\n";
  ServoControlState* states[] = {&servoAState, &servoBState, &servoCState, &servoDState};
  unsigned long now = millis();
  for (int i = 0; i < 4; ++i) {
      status += String(states[i]->id) + ": ";
      if (states[i]->isRunning) { status += String(states[i]->isForward ? "FWD" : "REV"); status += " (Speed " + String(states[i]->isForward ? states[i]->forwardSpeed : states[i]->reverseSpeed) + ")"; unsigned long remaining_ms = (states[i]->stopTime > now) ? (states[i]->stopTime - now) : 0; status += " Rem: " + String(remaining_ms / 1000.0, 1) + "s"; }
      else { status += "STOPPED (Speed " + String(SERVO_STOP_SPEED) + ")"; }
      status += " | ";
  }
  if (status.endsWith(" | ")) { status = status.substring(0, status.length() - 3); }
  status += "\n--- System Status ---\n";
  status += "Command Queue: " + String(queueCount) + "/" + String(QUEUE_SIZE) + "\n";
  status += "Delay Active: " + String(millis() < generalDelayEndTime ? "YES (" + String((generalDelayEndTime - millis())/1000.0, 1) + "s left)" : "NO") + "\n";
  status += "Uptime: " + String(millis() / 1000) + " s\n";

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
    switch (type) { case CMD_R: return 'R'; case CMD_G: return 'G'; case CMD_P: return 'P'; case CMD_H: return 'H'; case CMD_S: return 'S'; case CMD_D: return 'D'; default: return '?'; }
}

// Executes the next command from the queue if available and no delay is active
void executeCommandFromQueue() {
  if (queueCount > 0 && millis() >= generalDelayEndTime) {
    Command cmd = cmdQueue[queueFront]; queueFront = (queueFront + 1) % QUEUE_SIZE; queueCount--;
    Serial.print("Executing Cmd: "); Serial.print(getCommandTypeChar(cmd.type)); Serial.print("-");
    switch (cmd.type) {
      case CMD_R: // Set Drum Target RPM (VESC2)
        Serial.println(String(cmd.value1));
        targetRpm2 = cmd.value1; // Update target RPM
        // Ramping happens continuously in updateVescControl()
        break;

      case CMD_G: // Set Grinder Target Current (VESC1) <-- CHANGED
        Serial.println(String(cmd.value1, 2) + " Amps"); // Print target current
        // Clamp value to 0-2A range and update target
        targetCurrent1 = constrain(cmd.value1, 0.0f, 2.0f);
        // Target current is sent periodically in updateVescControl()
        break;

      case CMD_P: // Start Water Dispensing
        Serial.println(String(cmd.value1, 1) + "-" + String(cmd.value2, 2));
        if (!dispensingActive) {
          targetVolumeML = cmd.value1; targetFlowRateMLPS = cmd.value2;
          dispensedVolumeML = 0.0; noInterrupts(); pulseCount = 0; interrupts();
          lastPulseCount = 0; lastPulsePrintTime = 0; currentFlowRateMLPS = 0.0;
          pidError = 0.0; lastError = 0.0; integralError = 0.0; derivativeError = 0.0; pidOutput = 0.0;
          feedforwardDuty = calculateFeedforwardDuty(targetFlowRateMLPS);
          dispenseStartTime = millis(); lastFlowCalcTime = dispenseStartTime; lastControlTime = dispenseStartTime;
          dispensingActive = true; pumpUsedSinceHeaterOn = true;
          Serial.print("  Starting dispense. Target: "); Serial.print(targetVolumeML); Serial.print("mL @ "); Serial.print(targetFlowRateMLPS); Serial.print("mL/s. FF Duty: "); Serial.println(feedforwardDuty);
          ledcWrite(PUMP_LEDC_CHANNEL, feedforwardDuty);
        } else { Serial.println("  Warning: Pump already dispensing."); }
        break;

      case CMD_H: // Set Heater Power
      {
        Serial.println(String(cmd.value1));
        int heaterDuty = map(constrain((int)cmd.value1, 0, 100), 0, 100, 0, 255);
        ledcWrite(HEATER_LEDC_CHANNEL, heaterDuty);
        heaterActive = (heaterDuty > 0);
        if (heaterActive) {
          heaterStartTime = millis();
          pumpUsedSinceHeaterOn = false;
          // Reset no-flow safety check state when heater turns ON <-- NEW
          noInterrupts();
          lastPulseCheckCount = pulseCount; // Initialize with current count
          interrupts();
          lastNoPulseTime = 0; // Reset timer
          Serial.println("  Heater ON");
        } else {
           Serial.println("  Heater OFF");
           lastNoPulseTime = 0; // Also reset timer if heater is turned off explicitly
        }
        break;
      }
      case CMD_S: // Start Servo Periodic Movement
        {
            float durationSeconds = cmd.value1; unsigned long durationMillis = (unsigned long)(durationSeconds * 1000.0f); unsigned long currentTime = millis(); ServoControlState* stateToUpdate = nullptr;
            Serial.print(cmd.id); Serial.print("-"); Serial.println(String(durationSeconds, 1) + "s");
            switch (cmd.id) { case 'A': stateToUpdate = &servoAState; break; case 'B': stateToUpdate = &servoBState; break; case 'C': stateToUpdate = &servoCState; break; case 'D': stateToUpdate = &servoDState; break; default: Serial.println("  Error: Invalid Servo ID!"); break; }
            if (stateToUpdate != nullptr) { stateToUpdate->isRunning = true; stateToUpdate->stopTime = currentTime + durationMillis; stateToUpdate->periodStartTime = currentTime; stateToUpdate->isForward = true; stateToUpdate->servoObject.write(stateToUpdate->forwardSpeed); Serial.print("  Servo "); Serial.print(cmd.id); Serial.print(" starting periodic run for "); Serial.print(durationSeconds, 1); Serial.println("s"); Serial.print("    -> Starting FORWARD (Speed: "); Serial.print(stateToUpdate->forwardSpeed); Serial.println(")"); }
        }
        break;

      case CMD_D: // Start General Delay
        Serial.println(String(cmd.value1, 0) + "ms");
        generalDelayEndTime = millis() + (unsigned long)cmd.value1;
        Serial.println("  Delaying execution...");
        break;

      default: Serial.println(" ERROR: Executing invalid command type!"); break;
    }
  }
}

// Manages the water pump state, flow calculation, and PID control when active
void updateWaterPump() {
  if (!dispensingActive) return; // Exit if pump not active
  unsigned long currentTime = millis();
  // --- Periodic Pulse Count Printing ---
  if (currentTime - lastPulsePrintTime >= PULSE_PRINT_INTERVAL) { noInterrupts(); unsigned long currentPulses = pulseCount; interrupts(); /*Serial.print("Pump Active - Ticks: "); Serial.println(currentPulses);*/ lastPulsePrintTime = currentTime; } // Commented out the actual print
  // --- Flow Rate Calculation Task ---
  if (currentTime - lastFlowCalcTime >= flowCalcInterval) { noInterrupts(); unsigned long currentPulses = pulseCount; interrupts(); unsigned long deltaPulses = currentPulses - lastPulseCount; float deltaTimeSeconds = (currentTime - lastFlowCalcTime) / 1000.0; lastFlowCalcTime = currentTime; lastPulseCount = currentPulses; if (deltaTimeSeconds > 0.001) { float pps = (float)deltaPulses / deltaTimeSeconds; float ticksPerML_est = getTicksPerML(currentFlowRateMLPS > 0.05 ? currentFlowRateMLPS : targetFlowRateMLPS); if (ticksPerML_est > 0.1) { currentFlowRateMLPS = pps / ticksPerML_est; dispensedVolumeML += (float)deltaPulses / ticksPerML_est; } else { currentFlowRateMLPS = 0.0; } } }
  // --- PID Control Task ---
  if (currentTime - lastControlTime >= controlInterval) { float dt = (currentTime - lastControlTime) / 1000.0; lastControlTime = currentTime; if (dt > 0.001) { pidError = targetFlowRateMLPS - currentFlowRateMLPS; integralError += pidError * dt; integralError = constrain(integralError, -maxIntegral, maxIntegral); derivativeError = (pidError - lastError) / dt; pidOutput = (kp * pidError) + (ki * integralError) + (kd * derivativeError); lastError = pidError; int totalDuty = calculateFeedforwardDuty(targetFlowRateMLPS) + (int)round(pidOutput); totalDuty = constrain(totalDuty, 0, 255); ledcWrite(PUMP_LEDC_CHANNEL, totalDuty); } }
  // --- Check Stop Condition ---
  if (dispensedVolumeML >= targetVolumeML) { ledcWrite(PUMP_LEDC_CHANNEL, 0); dispensingActive = false; unsigned long duration = millis() - dispenseStartTime; Serial.println("\n--- Dispense Complete ---"); Serial.print("Target Vol: "); Serial.print(targetVolumeML, 1); Serial.println(" mL"); Serial.print("Actual Vol: "); Serial.print(dispensedVolumeML, 1); Serial.println(" mL"); Serial.print("Target Rate: "); Serial.print(targetFlowRateMLPS, 2); Serial.println(" mL/s"); if (duration > 0) { float avgFlowRate = (dispensedVolumeML / ((float)duration / 1000.0)); Serial.print("Average Rate: "); Serial.print(avgFlowRate, 2); Serial.println(" mL/s"); } Serial.print("Duration: "); Serial.print(duration); Serial.println(" ms"); noInterrupts(); Serial.print("Final Pulse Count: "); Serial.println(pulseCount); interrupts(); Serial.println("-------------------------"); if (heaterActive) { generalDelayEndTime = millis() + POST_PUMP_COOLDOWN; Serial.println("Heater cooldown started (" + String(POST_PUMP_COOLDOWN) + "ms)"); } }
}

// Updates VESC control signals
// VESC1=Grinder (Current), VESC2=Drum (RPM)
void updateVescControl() {
  uint32_t now_us = micros(); // Use microseconds for finer control interval

  // Send Target Current for VESC1 (Grinder) periodically <-- CHANGED
  if ((now_us - lastCurrentSendTime) >= CURRENT_SEND_INTERVAL_US) {
    vesc1.setCurrent(targetCurrent1); // Send the target current directly
    lastCurrentSendTime = now_us;    // Reset timer
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
  if (!state.isRunning) return; unsigned long currentTime = millis();
  if (currentTime >= state.stopTime) { state.servoObject.write(SERVO_STOP_SPEED); state.isRunning = false; Serial.print("Servo "); Serial.print(state.id); Serial.println(" stopped (Total time elapsed). Speed: " + String(SERVO_STOP_SPEED)); return; }
  unsigned long timeInPeriod = currentTime - state.periodStartTime;
  if (state.isForward) { if (timeInPeriod >= FORWARD_DURATION_MS) { state.servoObject.write(state.reverseSpeed); state.isForward = false; Serial.print("Servo "); Serial.print(state.id); Serial.print(" switching to REVERSE (Speed: "); Serial.print(state.reverseSpeed); Serial.println(")"); } }
  else { if (timeInPeriod >= SERVO_PERIOD_MS) { state.servoObject.write(state.forwardSpeed); state.isForward = true; state.periodStartTime = currentTime; Serial.print("Servo "); Serial.print(state.id); Serial.print(" switching to FORWARD (Speed: "); Serial.print(state.forwardSpeed); Serial.println(")"); } }
}


// Checks for safety conditions
void checkSafetyFeatures() {
    unsigned long currentTime = millis();

    // 1. Heater Timeout: Turn off heater if it's been on too long without pump usage
    if (heaterActive && !pumpUsedSinceHeaterOn && (currentTime - heaterStartTime > HEATER_TIMEOUT)) {
        Serial.println("Safety Trigger: Heater timed out (pump not used). Turning OFF.");
        ledcWrite(HEATER_LEDC_CHANNEL, 0); // Turn off heater PWM
        heaterActive = false;              // Update state flag
        lastNoPulseTime = 0; // Reset no-flow timer as well when heater turns off
    }

    // 2. No-Flow Timeout: Turn off heater if it's on but no flow detected <-- NEW / RE-ADDED
    if (heaterActive) {
        unsigned long currentPulses;
        noInterrupts(); // Safely read volatile pulseCount
        currentPulses = pulseCount;
        interrupts();

        if (currentPulses == lastPulseCheckCount) {
            // No change in pulses since last check
            if (lastNoPulseTime == 0) {
                // Start the timer if it wasn't already running
                lastNoPulseTime = currentTime;
            } else {
                // Timer was already running, check if timeout exceeded
                if (currentTime - lastNoPulseTime > NO_FLOW_TIMEOUT) {
                    Serial.println("Safety Trigger: Heater ON but no flow detected for > " + String(NO_FLOW_TIMEOUT) + "ms. Turning OFF.");
                    ledcWrite(HEATER_LEDC_CHANNEL, 0); // Turn off heater PWM
                    heaterActive = false;              // Update state flag
                    lastNoPulseTime = 0; // Reset timer after triggering
                }
            }
        } else {
            // Flow detected (pulse count changed), reset the timer
            lastNoPulseTime = 0;
        }
        // Update the count for the *next* check AFTER comparison
        lastPulseCheckCount = currentPulses;
    } else {
         // If heater is OFF, ensure the no-flow timer is reset
         lastNoPulseTime = 0;
    }


    // 3. Heater Cooldown after Pump: Turn off heater after post-pump delay
    if (!dispensingActive && heaterActive && generalDelayEndTime > 0 && currentTime >= generalDelayEndTime) {
        // Calculate roughly when the pump actually stopped
        unsigned long actualPumpStopTime = dispenseStartTime + (unsigned long)((dispensedVolumeML / (targetFlowRateMLPS > 0 ? targetFlowRateMLPS : 1.0)) * 1000.0);
        // Check if the general delay ended shortly after the pump stopped + cooldown period
        if (generalDelayEndTime > actualPumpStopTime && generalDelayEndTime < (actualPumpStopTime + POST_PUMP_COOLDOWN + 200) ) {
           Serial.println("Heater post-pump cooldown finished. Turning OFF.");
           ledcWrite(HEATER_LEDC_CHANNEL, 0); // Turn off heater PWM
           heaterActive = false;              // Update state flag
           lastNoPulseTime = 0; // Reset no-flow timer as well
        }
    }
}


// ==========================================================
// --- ESP32 Setup ---
// ==========================================================
void setup() {
  Serial.begin(SERIAL_BAUD); while (!Serial && millis() < 2000);
  Serial.println("\n\n--- Combined Control System Initializing ---");

  pinMode(OE_PIN, OUTPUT); digitalWrite(OE_PIN, HIGH); Serial.println("Logic Level Shifter Enabled (Pin " + String(OE_PIN) + ")");
  // VESC Setup (VESC1=Grinder/Current, VESC2=Drum/RPM)
  Serial1.begin(SERIAL_BAUD, SERIAL_8N1, VESC1_RX_PIN, VESC1_TX_PIN); // Grinder VESC UART
  Serial2.begin(SERIAL_BAUD, SERIAL_8N1, VESC2_RX_PIN, VESC2_TX_PIN); // Drum VESC UART
  vesc1.setSerialPort(&Serial1); vesc2.setSerialPort(&Serial2); Serial.println("VESC UART Ports Initialized (VESC1=Grinder Current, VESC2=Drum RPM)."); // <-- Updated comment
  // Pump Setup
  pinMode(PUMP_PWM_PIN, OUTPUT); ledcSetup(PUMP_LEDC_CHANNEL, PWM_FREQ, PWM_RES); ledcAttachPin(PUMP_PWM_PIN, PUMP_LEDC_CHANNEL); ledcWrite(PUMP_LEDC_CHANNEL, 0); pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP); attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), flowISR, RISING); Serial.println("Water Pump & Flow Sensor Initialized.");
  // Heater Setup
  pinMode(HEATER_PIN, OUTPUT); ledcSetup(HEATER_LEDC_CHANNEL, PWM_FREQ, PWM_RES); ledcAttachPin(HEATER_PIN, HEATER_LEDC_CHANNEL); ledcWrite(HEATER_LEDC_CHANNEL, 0); Serial.println("Heater Initialized.");
  // Servo Setup
  ESP32PWM::allocateTimer(0); ESP32PWM::allocateTimer(1); ESP32PWM::allocateTimer(2); ESP32PWM::allocateTimer(3); servoA.attach(SERVO_PIN_A); servoB.attach(SERVO_PIN_B); servoC.attach(SERVO_PIN_C); servoD.attach(SERVO_PIN_D); servoA.write(SERVO_STOP_SPEED); servoB.write(SERVO_STOP_SPEED); servoC.write(SERVO_STOP_SPEED); servoD.write(SERVO_STOP_SPEED); Serial.println("Servos Initialized & Stopped (Speed: " + String(SERVO_STOP_SPEED) + ").");

#ifdef WEB_MODE
  Serial.print("Connecting to WiFi: "); Serial.println(ssid); WiFi.begin(ssid, password); int wifi_retries = 0; while (WiFi.status() != WL_CONNECTED && wifi_retries < 20) { delay(500); Serial.print("."); wifi_retries++; } if (WiFi.status() == WL_CONNECTED) { Serial.println("\nWiFi Connected!"); Serial.print("IP Address: "); Serial.println(WiFi.localIP()); server.on("/", HTTP_GET, handleRoot); server.on("/command", HTTP_POST, handleCommand); server.on("/status", HTTP_GET, handleStatus); server.onNotFound(handleNotFound); server.begin(); Serial.println("Web Server Started."); } else { Serial.println("\nWiFi Connection Failed!"); }
#endif

  Serial.println("\n--- System Ready ---");
  Serial.println("Format examples:");
  Serial.println("  R-<rpm>           (Drum RPM, e.g., R-3000)");
  Serial.println("  G-<amps>          (Grinder Current 0.0-2.0A, e.g., G-1.5)"); // <-- Updated Help
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
  server.handleClient();
  // MDNS.update(); // Call if using mDNS
#endif

// Process Serial Input only if SERIAL_MODE is defined OR if WEB_MODE is disabled
// Note: Your code currently has WEB_MODE defined and SERIAL_MODE commented out
#if defined(SERIAL_MODE) || !defined(WEB_MODE)
  while (Serial.available() > 0) { char c = Serial.read(); if (c == '\n' || c == '\r') { serialInputBuffer.trim(); if (serialInputBuffer.length() > 0) { Serial.println("Received Serial Command: " + serialInputBuffer); int requiredSlots = countValidCommandsInString(serialInputBuffer); int availableSlots = QUEUE_SIZE - queueCount; if (requiredSlots == 0) { Serial.println("No valid commands."); } else if (requiredSlots > availableSlots) { Serial.println("Queue full. Req: " + String(requiredSlots) + ", Avail: " + String(availableSlots)); } else { processAndEnqueueCommands(serialInputBuffer); } } serialInputBuffer = ""; } else if (isprint(c) && serialInputBuffer.length() < 200) { serialInputBuffer += c; } }
#endif

  updateVescControl(); // Handles VESC commands (Current for VESC1, RPM for VESC2)
  updateWaterPump();   // Handles pump PID control, volume check, tick printing
  // Update servo states (periodic motion, stopping)
  updateServo(servoAState); updateServo(servoBState); updateServo(servoCState); updateServo(servoDState);
  executeCommandFromQueue(); // Execute next command if available
  checkSafetyFeatures();     // Run safety checks
  yield();                   // Allow background tasks
}
