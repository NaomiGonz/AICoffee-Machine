#include <Arduino.h>
#include <math.h>       // For pow() in pump control
#include <ESP32Servo.h> // For servos
#include "VescUart.h"   // For VESC control

// --- Operation Mode ---
// #define WEB_MODE      // Uncomment for Web Server control
#define SERIAL_MODE // Uncomment for Serial Monitor control

#ifdef WEB_MODE
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#endif

// ==========================================================
// --- Pin Definitions  ---
// ==========================================================

// VESC Control (Barrel = VESC1/RPM, Grinder = VESC2/Duty)
const int VESC1_RX_PIN = 16; // Serial1 RX for Barrel Motor VESC
const int VESC1_TX_PIN = 17; // Serial1 TX for Barrel Motor VESC
const int VESC2_RX_PIN = 12; // Serial2 RX for Grinder Motor VESC
const int VESC2_TX_PIN = 13; // Serial2 TX for Grinder Motor VESC

// Heater Control
const int HEATER_PIN = 23; // Heater PWM pin

// Logic Level Shifter Enable Pin (Active HIGH)
const int OE_PIN = 8; // Used for Flow Sensor, and Servos 

// Water Pump Control (L298N) 
const int PUMP_PWM_PIN    = 18; // L298N IN1 (or equivalent PWM input)
const int FLOW_SENSOR_PIN = 10; // Flow sensor interrupt pin 

// Servo Control 
const int SERVO_PIN_A = 4;
const int SERVO_PIN_B = 5;
const int SERVO_PIN_C = 6;
const int SERVO_PIN_D = 7;

// ==========================================================
// --- Configuration & Calibration ---
// ==========================================================

// Serial Baud Rate
#define SERIAL_BAUD 115200

// PWM Configuration
#define PWM_FREQ 5000 // PWM Frequency for Heater/Pump
#define PWM_RES 8     // PWM Resolution (0-255)
enum PWMLedcChannels {
  PUMP_LEDC_CHANNEL   = 0, // LEDC Channel for Pump
  HEATER_LEDC_CHANNEL = 1  // LEDC Channel for Heater
};

// VESC Ramping Configuration
#define RPM_STEP_SIZE          7.0f   // Barrel motor RPM step
#define RPM_STEP_INTERVAL_US   100UL  // Barrel motor step interval (micros)
#define DUTY_STEP_SIZE         0.001f // Grinder motor Duty step
#define DUTY_STEP_INTERVAL_US  500UL  // Grinder motor step interval (micros)

// Water Pump Flow Sensor Calibration (Copied from pump code)
// Ticks/mL = -0.0792 * (FlowRate)^2 + 1.0238 * (FlowRate) + 1.2755
// FlowRate (mL/s) = 0.0343 * Duty - 1.0155  => Duty = (FlowRate + 1.0155) / 0.0343

// Water Pump PID Controller Gains
float kp = 15.0;
float ki = 30.0;
float kd = 0.5;
float maxIntegral = 100.0; // Anti-windup limit

// Water Pump Control Intervals
const unsigned long flowCalcInterval = 100; // ms
const unsigned long controlInterval = 50;   // ms

// Servo Target Angles (Used when S command is received) & Off Angle
const int SERVO_A_TARGET_ANGLE = 45;
const int SERVO_B_TARGET_ANGLE = 45;
const int SERVO_C_TARGET_ANGLE = 45;
const int SERVO_D_TARGET_ANGLE = 45;
const int SERVO_OFF_ANGLE = 90; // Angle to set when timed operation ends

// Coffee Machine Safety Parameters
#define HEATER_TIMEOUT 5000     // Heater auto-off if pump not used (ms)
#define POST_PUMP_COOLDOWN 1000 // Heater off delay after pump stops (ms)
#define QUEUE_SIZE 20           // Command queue capacity

#ifdef WEB_MODE
// WiFi Configuration 
const char* ssid = "WIFI_NAME";
const char* password = "WIFI_PASSWORD";
WebServer server(80);
#endif

// ==========================================================
// --- Global Variables & Objects ---
// ==========================================================

// VESC Objects and State
VescUart vesc1; // Barrel Motor (RPM Control)
VescUart vesc2; // Grinder Motor (Duty Control)
float currentRpm1 = 0.0f;
float targetRpm1  = 0.0f;
float currentDuty2 = 0.0f;
float targetDuty2  = 0.0f;
uint32_t lastRpmStepTime  = 0;
uint32_t lastDutyStepTime = 0;

// Water Pump State & Control Variables
volatile unsigned long pulseCount = 0;
unsigned long lastPulseCount = 0;
float dispensedVolumeML = 0.0;
float currentFlowRateMLPS = 0.0;
float targetVolumeML = 0.0;
float targetFlowRateMLPS = 0.0;
bool dispensingActive = false;
unsigned long lastFlowCalcTime = 0;
unsigned long lastControlTime = 0;
float pidError = 0.0;
float lastError = 0.0;
float integralError = 0.0;
float derivativeError = 0.0;
float pidOutput = 0.0;
int feedforwardDuty = 0;
unsigned long dispenseStartTime = 0;

// Servo Objects and State
Servo servoA;
Servo servoB;
Servo servoC;
Servo servoD;
unsigned long servoEndTimes[4] = {0, 0, 0, 0}; // 0:A, 1:B, 2:C, 3:D. Stores millis() when servo should turn off.

// Coffee Machine State & Command Queue
bool heaterActive = false;
bool pumpUsedSinceHeaterOn = false; // For heater safety timeout
unsigned long heaterStartTime = 0;   // For heater safety timeout
unsigned long generalDelayEndTime = 0; // For 'D' command

enum CommandType { CMD_R, CMD_G, CMD_P, CMD_H, CMD_S, CMD_D, CMD_INVALID };
struct Command {
  CommandType type;
  float value1 = 0; // RPM, Duty, Volume, Power, Delay(ms) 
  float value2 = 0; // Flow Rate, Servo Duration(ms)
  char id = ' ';    // Servo ID (A, B, C, D)
};
Command cmdQueue[QUEUE_SIZE];
int queueFront = 0, queueRear = 0, queueCount = 0;

// For Serial Input Buffering
String serialInputBuffer = "";

// ==========================================================
// --- Interrupt Service Routines (For Flow Rate) ---
// ==========================================================
void IRAM_ATTR flowISR() {
  // DO NOT ADD ANYTHING ELSE HERE
  pulseCount++;
}

// ==========================================================
// --- Helper Functions ---
// ==========================================================

// --- Water Pump Helpers ---
float getTicksPerML(float flowRate) {
  // Apply the calibration curve: Ticks/mL = -0.0792x^2 + 1.0238x + 1.2755
  float ticks = -0.0792 * pow(flowRate, 2) + 1.0238 * flowRate + 1.2755;
  if (ticks <= 0.1) {
      if (flowRate < 0.1 && targetFlowRateMLPS > 0.1) {
          ticks = -0.0792 * pow(targetFlowRateMLPS, 2) + 1.0238 * targetFlowRateMLPS + 1.2755;
          if (ticks <= 0.1) return 1.0; // Absolute fallback
          return ticks;
      }
      return 1.0; // Default fallback
  }
  return ticks;
}

int calculateFeedforwardDuty(float targetRate) {
  // Invert the flow rate vs duty equation: Duty = (FlowRate + 1.0155) / 0.0343
  if (targetRate <= 0) return 0;
  float dutyFloat = (targetRate + 1.0155) / 0.0343;
  return constrain((int)round(dutyFloat), 0, 255);
}

// --- VESC Ramping Helpers ---
void stepRpm() {
  float diff = targetRpm1 - currentRpm1;
  if (fabs(diff) <= RPM_STEP_SIZE) {
    currentRpm1 = targetRpm1;
  } else {
    currentRpm1 += (diff > 0 ? RPM_STEP_SIZE : -RPM_STEP_SIZE);
  }
}

void stepDuty() {
  float diff = targetDuty2 - currentDuty2;
  if (fabs(diff) <= DUTY_STEP_SIZE) {
    currentDuty2 = targetDuty2;
  } else {
    currentDuty2 += (diff > 0 ? DUTY_STEP_SIZE : -DUTY_STEP_SIZE);
  }
   currentDuty2 = constrain(currentDuty2, -1.0f, 1.0f); // Ensure duty stays within bounds
}

// --- Command Processing Helpers ---

// Parses a single command token (e.g., "R-1000", "P-50-2.5", "S-A-5")
// Returns a Command struct (type will be CMD_INVALID if parsing fails)
Command parseToken(const String& token) {
  Command cmd;
  cmd.type = CMD_INVALID; // Default to invalid

  if (token.length() < 3 || token[1] != '-') {
      //Serial.println("Invalid format (must be X-...). Token: " + token); // Reduce noise
      return cmd;
   }

  char cmdType = toupper(token[0]);
  String params = token.substring(2); // Parameters after "X-"

  switch (cmdType) {
    case 'R': // R-<rpm>
      cmd.type = CMD_R;
      cmd.value1 = params.toFloat();
      break;
    case 'G': // G-<duty>
      cmd.type = CMD_G;
      cmd.value1 = params.toFloat();
      if (cmd.value1 < -1.0 || cmd.value1 > 1.0) {
         Serial.println("Warning: Duty cycle " + String(cmd.value1) + " out of range (-1.0 to 1.0). Clamping may occur.");
      }
      break;
    case 'P': // P-<volume>-<rate>
      { 
        int dashIndex = params.indexOf('-');
        if (dashIndex != -1) {
          cmd.type = CMD_P;
          cmd.value1 = params.substring(0, dashIndex).toFloat(); // Volume
          cmd.value2 = params.substring(dashIndex + 1).toFloat(); // Rate
          if (cmd.value1 <= 0 || cmd.value2 <= 0) {
             Serial.println("Invalid P command values (must be > 0). Token: " + token);
             cmd.type = CMD_INVALID; // Invalid params
          }
        } else {
           Serial.println("Invalid P command format (P-vol-rate). Token: " + token);
        }
      }
      break;
    case 'H': // H-<power>
      cmd.type = CMD_H;
      cmd.value1 = params.toFloat(); // Power %
      if (cmd.value1 < 0 || cmd.value1 > 100) {
         Serial.println("Invalid H command value (0-100). Token: " + token);
         cmd.type = CMD_INVALID;
      }
      break;
    case 'S': // S-<id>-<time_sec> 
      { 
         char servoIdChar = toupper(params[0]); 
         int dashIndex = params.indexOf('-');
         if (dashIndex != -1 && dashIndex == 1 && params.length() > dashIndex + 1) { // Ensure format like "A-5"
            cmd.id = toupper(params[0]); // Servo ID (A, B, C, D)
            float durationSec = params.substring(dashIndex + 1).toFloat(); // Duration in seconds

            if ((cmd.id >= 'A' && cmd.id <= 'D') && durationSec > 0) {
                cmd.type = CMD_S;
                cmd.value2 = durationSec * 1000.0f; // Store duration in milliseconds
            } else {
                Serial.println("Invalid S command values (ID A-D, time > 0 sec). Token: " + token);
                cmd.type = CMD_INVALID; // Invalid params
            }
         } else {
             Serial.println("Invalid S command format (S-ID-time_sec). Token: " + token);
         }
      }
      break;
    case 'D': // D-<time_ms>
      cmd.type = CMD_D;
      cmd.value1 = params.toFloat(); // Delay time in milliseconds
      if (cmd.value1 <= 0) {
         Serial.println("Invalid D command value (>0 ms). Token: " + token);
         cmd.type = CMD_INVALID;
      }
      break;
    default:
      Serial.println("Unknown command type '" + String(cmdType) + "'. Token: " + token);
      break; // Stays CMD_INVALID
  }

//   if(cmd.type == CMD_INVALID && token.length() > 0) { // Reduce noise, only print if parsing failed on non-empty token
//       Serial.println("Command parsing failed for: " + token);
//   }
  return cmd;
}


// Counts the number of valid command tokens in a space-separated string
int countValidCommandsInString(const String& input) {
    String currentToken;
    int validCount = 0;
    for (int i = 0; i < input.length(); i++) {
        if (input[i] == ' ' || i == input.length() - 1) {
            if (i == input.length() - 1 && input[i] != ' ') { // Include last char if not a space
                currentToken += input[i];
            }
            currentToken.trim();
            if (currentToken.length() > 0) {
                Command tempCmd = parseToken(currentToken); // Parse but don't queue
                if (tempCmd.type != CMD_INVALID) {
                    validCount++;
                }
            }
            currentToken = ""; // Reset for next token
        } else {
            currentToken += input[i];
        }
    }
    return validCount;
}

// Parses command string and ENQUEUES valid commands *IF* they were pre-validated for space
void processAndEnqueueCommands(const String& input) {
    String currentToken;
    int cmdAddedCount = 0;
    for (int i = 0; i < input.length(); i++) {
        if (input[i] == ' ' || i == input.length() - 1) {
            if (i == input.length() - 1 && input[i] != ' ') { // Include last char if not a space
                currentToken += input[i];
            }
            currentToken.trim();
            if (currentToken.length() > 0) {
                Command cmd = parseToken(currentToken);
                if (cmd.type != CMD_INVALID) {
                    // Add to queue (space was already checked)
                     if (queueCount < QUEUE_SIZE) {
                        cmdQueue[queueRear] = cmd;
                        queueRear = (queueRear + 1) % QUEUE_SIZE;
                        queueCount++;
                        cmdAddedCount++;
                    } else {
                         // Should not happen if pre-check worked, but as a safeguard:
                         Serial.println("ERROR: Queue full during enqueue - Pre-check failed?");
                         break; // Stop processing this string if queue is unexpectedly full
                    }
                }
            }
            currentToken = ""; // Reset for next token
        } else {
            currentToken += input[i];
        }
    }
     if (cmdAddedCount > 0) {
        Serial.print(cmdAddedCount);
        Serial.println(" command(s) successfully queued.");
    }
}


#ifdef WEB_MODE
// ==========================================================
// --- Web Server Handlers ---
// ==========================================================
void handleRoot() {
  // Simple HTML form
  String html = R"(
  <!DOCTYPE html><html><head><title>ESP32 Control</title>
  <style>body{font-family: sans-serif;} label{display: block; margin-top: 10px;}</style>
  </head><body><h1>ESP32 Device Control</h1>
  <form action='/command' method='POST'>
    <label for='cmd'>Command String:</label>
    <input type='text' id='cmd' name='cmd' size='50' placeholder='e.g., R-1000 G-0.5 P-50-2.0 H-75 S-A-5 D-1000'>
    <button type='submit'>Send</button>
  </form>
  <h2>Status</h2>
  <pre id='status'>Loading...</pre>
  <script>
    function updateStatus() {
      fetch('/status').then(r=>r.text()).then(t=>document.getElementById('status').textContent=t)
                     .catch(e=>document.getElementById('status').textContent='Error fetching status.');
    }
    setInterval(updateStatus, 2000); // Update every 2 seconds
    updateStatus(); // Initial load
  </script>
  </body></html>)";
  server.send(200, "text/html", html);
}

void handleCommand() {
  if (!server.hasArg("cmd")) {
    server.send(400, "text/plain", "Bad Request: Missing 'cmd' argument.");
    return;
  }
  String input = server.arg("cmd");
  input.trim();
  Serial.println("Received Web Command: " + input);

  if (input.length() == 0) {
      server.send(400, "text/plain", "Bad Request: Empty command string.");
      return;
  }

  // --- Queue Pre-Check ---
  int requiredSlots = countValidCommandsInString(input);
  int availableSlots = QUEUE_SIZE - queueCount;

  if (requiredSlots == 0) {
       server.send(400, "text/plain", "No valid commands found in the input string.");
  } else if (requiredSlots > availableSlots) {
      String msg = "Queue full. Required: " + String(requiredSlots) +
                   ", Available: " + String(availableSlots) + ". Command rejected.";
      server.send(503, "text/plain", msg); // 503 Service Unavailable
      Serial.println(msg);
  } else {
      // --- Enqueue Commands ---
      processAndEnqueueCommands(input); // Parse again and add to queue
      String msg = String(requiredSlots) + " command(s) accepted. Queue: " +
                   String(queueCount) + "/" + String(QUEUE_SIZE);
      server.send(200, "text/plain", msg);
  }
}

void handleStatus() {
  String status = "--- VESC Status ---\n";
  status += "Barrel (RPM): Target=" + String(targetRpm1) + ", Current=" + String(currentRpm1, 0) + "\n";
  status += "Grinder (Duty): Target=" + String(targetDuty2, 3) + ", Current=" + String(currentDuty2, 3) + "\n";
  status += "--- Water Pump Status ---\n";
  status += "State: " + String(dispensingActive ? "DISPENSING" : "IDLE") + "\n";
  status += "Target: " + String(targetVolumeML, 1) + " mL @ " + String(targetFlowRateMLPS, 2) + " mL/s\n";
  status += "Current: " + String(dispensedVolumeML, 1) + " mL / " + String(currentFlowRateMLPS, 2) + " mL/s\n";
  status += "--- Heater Status ---\n";
  status += "State: " + String(heaterActive ? "ON" : "OFF") + "\n";
  status += "--- Servo Status ---\n";
  // Show correct target angle based on which servo is active
  int targetAngleA = servoEndTimes[0] > 0 ? SERVO_A_TARGET_ANGLE : SERVO_OFF_ANGLE;
  int targetAngleB = servoEndTimes[1] > 0 ? SERVO_B_TARGET_ANGLE : SERVO_OFF_ANGLE;
  int targetAngleC = servoEndTimes[2] > 0 ? SERVO_C_TARGET_ANGLE : SERVO_OFF_ANGLE;
  int targetAngleD = servoEndTimes[3] > 0 ? SERVO_D_TARGET_ANGLE : SERVO_OFF_ANGLE;
  status += "A Pos:" + String(servoA.read()) + " Target:" + String(targetAngleA) + " | ";
  status += "B Pos:" + String(servoB.read()) + " Target:" + String(targetAngleB) + " | ";
  status += "C Pos:" + String(servoC.read()) + " Target:" + String(targetAngleC) + " | ";
  status += "D Pos:" + String(servoD.read()) + " Target:" + String(targetAngleD) + "\n";
  status += "--- System Status ---\n";
  status += "Command Queue: " + String(queueCount) + "/" + String(QUEUE_SIZE) + "\n";
  status += "Delay Active: " + String(millis() < generalDelayEndTime ? "YES" : "NO") + "\n";

  server.send(200, "text/plain", status);
}

void handleNotFound() {
  server.send(404, "text/plain", "Not Found.");
}
#endif // WEB_MODE

// ==========================================================
// --- Core Logic Functions ---
// ==========================================================

// Helper to get the character for the command type
char getCommandTypeChar(CommandType type) {
    switch (type) {
        case CMD_R: return 'R';
        case CMD_G: return 'G';
        case CMD_P: return 'P';
        case CMD_H: return 'H';
        case CMD_S: return 'S';
        case CMD_D: return 'D';
        default: return '?';
    }
}


void executeCommandFromQueue() {
  if (queueCount > 0 && millis() >= generalDelayEndTime) { // Only execute if no general delay active
    Command cmd = cmdQueue[queueFront];
    queueFront = (queueFront + 1) % QUEUE_SIZE;
    queueCount--;

    Serial.print("Executing Cmd: ");
    if (cmd.type == CMD_S) {
         Serial.print("S-"); Serial.print(cmd.id); // Show Servo ID for S command
    } else {
         Serial.print(getCommandTypeChar(cmd.type)); // Show command type char
    }
     Serial.print("..."); // Indicate execution start

    switch (cmd.type) {
      case CMD_R: // Set Barrel Target RPM
        Serial.println(" R-" + String(cmd.value1));
        targetRpm1 = cmd.value1;
        // Ramping happens continuously in loop()
        break;

      case CMD_G: // Set Grinder Target Duty
        Serial.println(" G-" + String(cmd.value1, 3));
        targetDuty2 = constrain(cmd.value1, -1.0f, 1.0f); // Apply constraints
        // Ramping happens continuously in loop()
        break;

      case CMD_P: // Start Water Dispensing
        Serial.println(" P-" + String(cmd.value1, 1) + "-" + String(cmd.value2, 2));
        if (!dispensingActive) { // Prevent starting if already running
          targetVolumeML = cmd.value1;
          targetFlowRateMLPS = cmd.value2;

          // Reset pump state variables
          dispensedVolumeML = 0.0;
          pulseCount = 0; // Reset volatile counter safely before starting
          lastPulseCount = 0;
          currentFlowRateMLPS = 0.0;
          pidError = 0.0;
          lastError = 0.0;
          integralError = 0.0;
          derivativeError = 0.0;
          pidOutput = 0.0;
          feedforwardDuty = calculateFeedforwardDuty(targetFlowRateMLPS);

          dispenseStartTime = millis();
          lastFlowCalcTime = dispenseStartTime;
          lastControlTime = dispenseStartTime;
          dispensingActive = true;
          pumpUsedSinceHeaterOn = true; // Mark pump as used for heater safety

          Serial.print("  Starting dispense. FF Duty: "); Serial.println(feedforwardDuty);
          ledcWrite(PUMP_LEDC_CHANNEL, feedforwardDuty); // Apply initial duty
        } else {
          Serial.println("  Warning: Cannot start pump, already dispensing.");
        }
        break;

      case CMD_H: // Set Heater Power
        Serial.println(" H-" + String(cmd.value1));
        int heaterDuty = map(constrain((int)cmd.value1, 0, 100), 0, 100, 0, 255);
        ledcWrite(HEATER_LEDC_CHANNEL, heaterDuty);
        heaterActive = (heaterDuty > 0);
        if (heaterActive) {
          heaterStartTime = millis();
          pumpUsedSinceHeaterOn = false; // Reset pump usage flag when heater turns on/changes
          Serial.println("  Heater ON");
        } else {
           Serial.println("  Heater OFF");
        }
        break;

      case CMD_S: // Set Servo Angle for a Duration (using TARGET angle)
        { 
            unsigned long duration = (unsigned long)cmd.value2; // Duration is already in ms
            unsigned long endTime = millis() + duration;
            int targetAngle = SERVO_OFF_ANGLE; // Default to off angle if ID invalid

            Serial.print("-"); // Continue debug print S-ID-...
            Serial.print(String(duration / 1000.0, 1)); // Print duration in seconds
            Serial.print("s -> ");

            switch (cmd.id) {
            case 'A':
                targetAngle = SERVO_A_TARGET_ANGLE;
                servoA.write(targetAngle);
                servoEndTimes[0] = endTime;
                Serial.println("A to " + String(targetAngle) + " deg");
                break;
            case 'B':
                targetAngle = SERVO_B_TARGET_ANGLE;
                servoB.write(targetAngle);
                servoEndTimes[1] = endTime;
                Serial.println("B to " + String(targetAngle) + " deg");
                break;
            case 'C':
                targetAngle = SERVO_C_TARGET_ANGLE;
                servoC.write(targetAngle);
                servoEndTimes[2] = endTime;
                 Serial.println("C to " + String(targetAngle) + " deg");
                break;
            case 'D':
                targetAngle = SERVO_D_TARGET_ANGLE;
                servoD.write(targetAngle);
                servoEndTimes[3] = endTime;
                Serial.println("D to " + String(targetAngle) + " deg");
                break;
             default: // Should have been caught by parser, but safety first
                 Serial.println(" Invalid Servo ID!");
                 break;
            }
        }
        break;

      case CMD_D: // Start General Delay
        Serial.println(" D-" + String(cmd.value1, 0) + "ms");
        generalDelayEndTime = millis() + (unsigned long)cmd.value1;
        Serial.println("  Delaying...");
        break;

      default: // Should not happen if parseToken works
        Serial.println(" ERROR: Executing invalid command type from queue!");
        break;
    }
  }
}

void updateWaterPump() {
  if (!dispensingActive) return;

  unsigned long currentTime = millis();

  // --- Flow Rate Calculation Task ---
  if (currentTime - lastFlowCalcTime >= flowCalcInterval) {
    // Safely read volatile pulseCount
    noInterrupts(); // Disable interrupts briefly
    unsigned long currentPulses = pulseCount;
    interrupts(); // Re-enable interrupts ASAP

    unsigned long deltaPulses = currentPulses - lastPulseCount;
    float deltaTimeSeconds = (currentTime - lastFlowCalcTime) / 1000.0;
    lastFlowCalcTime = currentTime; // Update time for next interval
    lastPulseCount = currentPulses; // Update count for next interval

    if (deltaTimeSeconds > 0.001) { // Avoid division by zero on rapid calls
        float pps = (float)deltaPulses / deltaTimeSeconds;
        // Estimate Ticks/mL based on *target* flow rate for stability, or last known rate
        float ticksPerML_est = getTicksPerML(currentFlowRateMLPS > 0.05 ? currentFlowRateMLPS : targetFlowRateMLPS);

        if (ticksPerML_est > 0.1) {
            currentFlowRateMLPS = pps / ticksPerML_est;
            // Update total dispensed volume using the most recent Ticks/mL estimation
            dispensedVolumeML += (float)deltaPulses / ticksPerML_est;
        } else {
            currentFlowRateMLPS = 0.0; // Assume zero flow if ticks/mL is invalid
        }
    }
     // Optional: Print Flow Rate Debug Info
     // Serial.print("Rate Calc: dT="); Serial.print(deltaTimeSeconds, 4); Serial.print(" dP="); Serial.print(deltaPulses);
     // Serial.print(" PPS="); Serial.print(pps, 2); Serial.print(" T/mL="); Serial.print(ticksPerML_est, 2);
     // Serial.print(" Flow="); Serial.print(currentFlowRateMLPS, 2); Serial.print(" Vol="); Serial.println(dispensedVolumeML, 1);
  }

  // --- PID Control Task ---
  if (currentTime - lastControlTime >= controlInterval) {
      float dt = (currentTime - lastControlTime) / 1000.0;
      lastControlTime = currentTime;

      if (dt > 0.001) {
          pidError = targetFlowRateMLPS - currentFlowRateMLPS;
          integralError += pidError * dt;
          integralError = constrain(integralError, -maxIntegral, maxIntegral); // Clamp integral term

          // Calculate Derivative
          derivativeError = (pidError - lastError) / dt;

          // Calculate PID Output
          pidOutput = (kp * pidError) + (ki * integralError) + (kd * derivativeError);

           // Update last error
           lastError = pidError;

          // --- Combine Feedforward and PID ---
          int totalDuty = feedforwardDuty + (int)round(pidOutput);

          // --- Constrain total duty cycle ---
          totalDuty = constrain(totalDuty, 0, 255);

          // --- Apply control signal to pump ---
          ledcWrite(PUMP_LEDC_CHANNEL, totalDuty);

          // Optional: Print PID Debug Info
           // Serial.print("PID: Err="); Serial.print(pidError, 2); Serial.print(" Int="); Serial.print(integralError, 2);
           // Serial.print(" Der="); Serial.print(derivativeError, 2); Serial.print(" Out="); Serial.print(pidOutput, 2);
           // Serial.print(" FF="); Serial.print(feedforwardDuty); Serial.print(" TotalDuty="); Serial.println(totalDuty);
      }
  }

  // --- Check Stop Condition ---
  if (dispensedVolumeML >= targetVolumeML) {
    ledcWrite(PUMP_LEDC_CHANNEL, 0); // Stop pump PWM
    // NO PUMP_OE_PIN toggle needed here
    dispensingActive = false;

    unsigned long duration = millis() - dispenseStartTime;
    Serial.println("\n--- Dispense Complete ---");
    Serial.print("Target Vol: "); Serial.print(targetVolumeML, 1); Serial.println(" mL");
    Serial.print("Actual Vol: "); Serial.print(dispensedVolumeML, 1); Serial.println(" mL");
    Serial.print("Target Rate: "); Serial.print(targetFlowRateMLPS, 2); Serial.println(" mL/s");
    if (duration > 0) {
        float avgFlowRate = (dispensedVolumeML / ((float)duration / 1000.0));
        Serial.print("Average Rate: "); Serial.print(avgFlowRate, 2); Serial.println(" mL/s");
    }
    Serial.print("Duration: "); Serial.print(duration); Serial.println(" ms");
    Serial.println("-------------------------");

    // If heater was active, potentially start cooldown delay
    if (heaterActive) {
        generalDelayEndTime = millis() + POST_PUMP_COOLDOWN; // Start post-pump heater cooldown delay
        Serial.println("Heater cooldown started (" + String(POST_PUMP_COOLDOWN) + "ms)");
    }
  }
}


void updateVescControl() {
  uint32_t now_us = micros();

  // Step VESC1 (RPM/Barrel) if interval passed
  if ((now_us - lastRpmStepTime) >= RPM_STEP_INTERVAL_US) {
    stepRpm();
    vesc1.setRPM((int32_t)currentRpm1); // Send updated RPM command
    lastRpmStepTime = now_us;
  }

  // Step VESC2 (Duty/Grinder) if interval passed
  if ((now_us - lastDutyStepTime) >= DUTY_STEP_INTERVAL_US) {
    stepDuty();
    vesc2.setDuty(currentDuty2); // Send updated Duty command
    lastDutyStepTime = now_us;
  }
}

void updateServos() {
  unsigned long currentTime = millis();
  Servo* servos[] = {&servoA, &servoB, &servoC, &servoD};
  for (int i = 0; i < 4; ++i) {
    if (servoEndTimes[i] != 0 && currentTime >= servoEndTimes[i]) {
      servos[i]->write(SERVO_OFF_ANGLE); // Move to off position
      servoEndTimes[i] = 0; // Mark as complete
       Serial.print("Servo "); Serial.print((char)('A' + i)); Serial.println(" timed operation complete. Set to " + String(SERVO_OFF_ANGLE));
    }
  }
}

void checkSafetyFeatures() {
    unsigned long currentTime = millis();

    // Heater Timeout: Turn off heater if it's been on too long without pump usage
    if (heaterActive && !pumpUsedSinceHeaterOn && (currentTime - heaterStartTime > HEATER_TIMEOUT)) {
        Serial.println("Safety Trigger: Heater timed out (pump not used). Turning OFF.");
        ledcWrite(HEATER_LEDC_CHANNEL, 0);
        heaterActive = false;
    }

    // Heater Cooldown after Pump: Turn off heater after post-pump delay, only if pump is NOT running
    // This relies on generalDelayEndTime being set correctly when the pump finishes.
    if (!dispensingActive && heaterActive && generalDelayEndTime > 0 && currentTime >= generalDelayEndTime) {
        // A simple check: if the delay just ended, assume it might be the cooldown.
        // More robust would be a dedicated flag `isHeaterCooldownDelayActive`.
        // For now, this should work if D commands aren't used immediately after pump stops.
        Serial.println("Heater post-pump cooldown finished. Turning OFF.");
        ledcWrite(HEATER_LEDC_CHANNEL, 0);
        heaterActive = false;
        // Consider resetting generalDelayEndTime here? No, it has naturally passed.
    }
}


// ==========================================================
// --- ESP32 Setup ---
// ==========================================================
void setup() {
  Serial.begin(SERIAL_BAUD);
  while (!Serial && millis() < 2000); // Wait a bit for serial monitor
  Serial.println("\n\n--- Combined Control System Initializing ---");

  // --- Logic Level Shifter Enable ---
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH); // Enable the shifter (Active HIGH assumed)
  Serial.println("Logic Level Shifter Enabled (Pin " + String(OE_PIN) + ")");

  // --- VESC Setup ---
  Serial1.begin(SERIAL_BAUD, SERIAL_8N1, VESC1_RX_PIN, VESC1_TX_PIN);
  Serial2.begin(SERIAL_BAUD, SERIAL_8N1, VESC2_RX_PIN, VESC2_TX_PIN);
  vesc1.setSerialPort(&Serial1);
  vesc2.setSerialPort(&Serial2);
  Serial.println("VESC UART Ports Initialized.");

  // --- Water Pump Setup ---
  pinMode(PUMP_PWM_PIN, OUTPUT);
  ledcSetup(PUMP_LEDC_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(PUMP_PWM_PIN, PUMP_LEDC_CHANNEL);
  ledcWrite(PUMP_LEDC_CHANNEL, 0); // Ensure pump is off
  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP); // Or INPUT if external pullup used
  // Attach interrupt AFTER setting up Serial/other peripherals potentially using timers/interrupts
  attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), flowISR, RISING);
  Serial.println("Water Pump & Flow Sensor Initialized.");

  // --- Heater Setup ---
  pinMode(HEATER_PIN, OUTPUT);
  ledcSetup(HEATER_LEDC_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(HEATER_PIN, HEATER_LEDC_CHANNEL);
  ledcWrite(HEATER_LEDC_CHANNEL, 0); // Ensure heater is off
  Serial.println("Heater Initialized.");

  // --- Servo Setup ---
  // Level shifter already enabled by OE_PIN setup
  ESP32PWM::allocateTimer(0); // Allocate timers for servos
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  servoA.attach(SERVO_PIN_A);
  servoB.attach(SERVO_PIN_B);
  servoC.attach(SERVO_PIN_C);
  servoD.attach(SERVO_PIN_D);
  servoA.write(SERVO_OFF_ANGLE); // Set initial positions
  servoB.write(SERVO_OFF_ANGLE);
  servoC.write(SERVO_OFF_ANGLE);
  servoD.write(SERVO_OFF_ANGLE);
  Serial.println("Servos Initialized.");

#ifdef WEB_MODE
  // --- WiFi & Web Server Setup ---
  Serial.print("Connecting to WiFi: "); Serial.println(ssid);
  WiFi.begin(ssid, password);
  int wifi_retries = 0;
  while (WiFi.status() != WL_CONNECTED && wifi_retries < 20) {
    delay(500);
    Serial.print(".");
    wifi_retries++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected!");
    Serial.print("IP Address: "); Serial.println(WiFi.localIP());

    if (MDNS.begin("esp32-control")) { // Set hostname for mDNS
      Serial.println("mDNS responder started (esp32-control.local)");
       MDNS.addService("http", "tcp", 80);
    } else {
       Serial.println("Error setting up mDNS responder!");
    }

    server.on("/", HTTP_GET, handleRoot);
    server.on("/command", HTTP_POST, handleCommand);
    server.on("/status", HTTP_GET, handleStatus);
    server.onNotFound(handleNotFound);
    server.begin();
    Serial.println("Web Server Started.");
  } else {
    Serial.println("\nWiFi Connection Failed!");
    // Consider fallback to Serial mode or error state?
  }
#endif // WEB_MODE

  Serial.println("\n--- System Ready ---");
  Serial.println("Enter commands via Serial Monitor or Web Interface (if enabled).");
  Serial.println("Format examples:");
  Serial.println("  R-<rpm>           (e.g., R-3000)");
  Serial.println("  G-<duty>          (e.g., G-0.75)");
  Serial.println("  P-<vol>-<rate>    (e.g., P-100-2.5)");
  Serial.println("  H-<power%>        (e.g., H-80)");
  Serial.println("  S-<id>-<time_sec> (e.g., S-A-5 --> Servo A to " + String(SERVO_A_TARGET_ANGLE) + "deg for 5s)");
  Serial.println("  D-<ms>            (e.g., D-2000 --> Delay 2s)");
  Serial.println("Combine commands with spaces.");
  Serial.println("--------------------");
}

// ==========================================================
// --- Arduino Loop ---
// ==========================================================
void loop() {

#ifdef WEB_MODE
  server.handleClient(); // Handle web requests
   MDNS.update(); // Keep mDNS active
#endif // WEB_MODE

#if defined(SERIAL_MODE) || !defined(WEB_MODE) // Allow Serial input if in SERIAL_MODE or if WEB_MODE is disabled
  // Handle Serial Input (non-blocking) with Pre-Check
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { // End of command line
      serialInputBuffer.trim();
      if (serialInputBuffer.length() > 0) {
        Serial.println("Received Serial Command: " + serialInputBuffer);

        // --- Queue Pre-Check ---
        int requiredSlots = countValidCommandsInString(serialInputBuffer);
        int availableSlots = QUEUE_SIZE - queueCount;

        if (requiredSlots == 0) {
             Serial.println("No valid commands found in the input string.");
        } else if (requiredSlots > availableSlots) {
            String msg = "Queue full. Required: " + String(requiredSlots) +
                         ", Available: " + String(availableSlots) + ". Command rejected.";
            Serial.println(msg);
        } else {
            // --- Enqueue Commands ---
            processAndEnqueueCommands(serialInputBuffer); // Parse again and add to queue
        }
      }
      serialInputBuffer = ""; // Clear buffer for next command
    } else if (serialInputBuffer.length() < 200) { // Increase buffer size slightly?
      serialInputBuffer += c;
    }
  }
#endif // SERIAL_MODE check

  // --- Continuous Operations ---
  updateVescControl(); // Update VESC ramping and send commands
  updateWaterPump();   // Update pump PID control if active
  updateServos();      // Check and disable timed servos

  // --- Command Queue Execution ---
  executeCommandFromQueue(); // Process one command if ready and no delay

  // --- Safety Checks ---
  checkSafetyFeatures(); // Check heater timeouts etc.

  // Yield allows background tasks (like WiFi) to run - Important for stability
  yield();
}










