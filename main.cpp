#include <Arduino.h>
#include <math.h>        
#include <ESP32Servo.h>  
#include "VescUart.h"    
#include <ctype.h>       

// --- Operation Mode ---
//#define WEB_MODE      // Uncomment for Web Server control
#define SERIAL_MODE  // Uncomment for Serial Monitor control (Can be active alongside WEB_MODE)

#ifdef WEB_MODE
#include <WiFi.h>
#include <WebServer.h>
#endif

// ==========================================================
// --- WiFi Credentials (if WEB_MODE enabled) ---
// ==========================================================
#ifdef WEB_MODE
const char* ssid = "Sebastian_Izzy";  // Replace with WiFi SSID
const char* password = "99999999";    // Replace with WiFi Password
WebServer server(80);
#endif

// ==========================================================
// --- Pin Definitions  ---
// ==========================================================

// VESC Control
// VESC1 = Grinder (Duty Control), VESC2 = Drum (RPM Control)
const int VESC1_RX_PIN = 12;  // Serial1 RX for GRINDER Motor VESC (Duty)
const int VESC1_TX_PIN = 13;  // Serial1 TX for GRINDER Motor VESC (Duty)
const int VESC2_RX_PIN = 16;  // Serial2 RX for DRUM Motor VESC (RPM)
const int VESC2_TX_PIN = 17;  // Serial2 TX for DRUM Motor VESC (RPM)

// Heater Control
const int HEATER_PIN = 38;  // Heater PWM pin

// Logic Level Shifter Enable Pin (Active HIGH)
const int OE_PIN = 8;  // Used for Flow Sensor and Servos

// Water Pump Control
const int PUMP_PWM_PIN = 40;     // Pin connected to PWM input of pump driver
const int FLOW_SENSOR_PIN = 10;  // Flow sensor interrupt pin 

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
#define PWM_FREQ 5000  // PWM Frequency for Heater/Pump
#define PWM_RES 8      // PWM Resolution (0-255)
enum PWMLedcChannels {
  PUMP_LEDC_CHANNEL = 4,   // LEDC Channel for Pump
  HEATER_LEDC_CHANNEL = 5  // LEDC Channel for Heater
};

// VESC Configuration (VESC1=Grinder/Duty, VESC2=Drum/RPM)
#define RPM_STEP_SIZE          7.0f   // Drum motor RPM step
#define RPM_STEP_INTERVAL_US   100UL  // Drum motor step interval (micros)
#define DUTY_STEP_SIZE         0.001f // Grinder motor Duty step
#define DUTY_STEP_INTERVAL_US  500UL  // Grinder motor step interval (micros)

// State machine for water pump control
enum FlowState { FLOW_IDLE,
                 FLOW_DISPENSING };
FlowState currentFlowState = FLOW_IDLE;

// --- Control Parameters ---
double targetFlowRate_mL_s = 1.0;           // Target flow rate in mL per second
double targetVolume_mL = 0.0;               // Target volume in mL for dispensing 
const unsigned long SAMPLE_TIME_MS = 1500;  // Measurement and control interval (1.5 seconds) for the Kalman/PID loop
const double MIN_FLOW_RATE = 1.0;           // mL/s 
const double MAX_FLOW_RATE = 8.0;           // mL/s

// --- Feed-Forward Equation Parameters (FlowRate_mL_s = A * DutyCycle + B) ---
// x = (y + 0.0907) / 0.0215 = 46.5116*y + 4.2186
const double FF_SLOPE = 46.5116;       // Slope for the feed-forward estimation (Duty = Slope * FlowRate + Intercept)
const double FF_INTERCEPT = 4.2186;  // Intercept for the feed-forward estimation

// --- Direct Ticks Per Milliliter Equation Parameters (TPmL = A*FlowRate^2 + B*FlowRate + C) ---
// TicksPerGram = -0.127*FlowRate^2 + 1.7044*FlowRate - 0.6559
const double TPmL_A = -0.127;   
const double TPmL_B = 1.7044;   
const double TPmL_C = -0.6559; 

// --- Kalman Filter Parameters ---
double Q_flow = 0.01;     // Process noise covariance - Represents uncertainty in the system model
double R_flow = 0.1;      // Measurement noise covariance - Represents uncertainty in the sensor reading
double x_hat_flow = 0.0;  // Estimated state (flow rate mL/s) - The Kalman filter's best guess of the current flow rate
double P_flow = 1.0;      // Estimate error covariance - Represents the filter's confidence in its estimate

// --- Manual PID Controller Parameters & Variables (for Pump) ---
double Kp_flow = 0.4;            // Proportional weight (reacts to current error)
double Ki_flow = 0.2;            // Integral weight (reacts to accumulated past error)
double Kd_flow = 0.4;            // Derivative weight (reacts to rate of change of error)
double overallGain_flow = 10.0;  // Overall PID strength multiplier

double pidSetpoint_flow;          // Target flow rate for PID controller 
double pidInput_flow;             // Measured (Kalman filtered) flow rate used as input to PID
double pidOutput_flow = 0.0;      // PID controller calculated output
double lastPidOutput_flow = 0.0;  // Stores last commanded PWM duty cycle, used for Kalman prediction step

// PID internal state
double integralTerm_flow = 0.0;  // Accumulates the integral error component
double lastError_flow = 0.0;     // Stores the error from the previous PID calculation for the derivative term

// --- Pulse Counting ---
volatile unsigned long pulseCount = 0;      // Incremented by ISR for each flow rate sensor pulse
unsigned long totalPulseCountDispense = 0;  // Total pulses during a single dispense operation

// --- Timing ---
unsigned long lastMeasurementTime = 0;  // Timer for the main flow control loop (SAMPLE_TIME_MS)

// --- Total Volume Calculation ---
double totalVolumeDispensed_mL = 0.0;  //Calculated volume dispensed during an operation (using TPmL)


// --- Servo Speed/Control Definitions ( 90=stop for continuous servos) ---
const int SERVO_STOP_SPEED = 90;
const int SERVO_A_FORWARD_SPEED = 135;
const int SERVO_A_REVERSE_SPEED = 45;
const int SERVO_B_FORWARD_SPEED = 135;
const int SERVO_B_REVERSE_SPEED = 45;
const int SERVO_C_FORWARD_SPEED = 135;
const int SERVO_C_REVERSE_SPEED = 45;
const int SERVO_D_FORWARD_SPEED = 45;
const int SERVO_D_REVERSE_SPEED = 135;

// --- Servo Dispensing Rate --- 
const double SERVO_GRAMS_PER_SECOND = 0.61; // Calibrated rate for calculating servo run time from grams

// --- Servo Periodic Motion Parameters ---
const int SERVO_PERIOD_SECONDS = 5;                                   // Total period duration in seconds (for forward/reverse cycle within total run time)
const unsigned long SERVO_PERIOD_MS = SERVO_PERIOD_SECONDS * 1000UL;  // Period in milliseconds
const float FORWARD_DUTY_CYCLE = 0.90;                                // 90% of the period forward
const float REVERSE_DUTY_CYCLE = 0.10;                                // 10% of the period reverse
// Calculated durations
const unsigned long FORWARD_DURATION_MS = (unsigned long)(SERVO_PERIOD_MS * FORWARD_DUTY_CYCLE);
const unsigned long REVERSE_DURATION_MS = (unsigned long)(SERVO_PERIOD_MS * REVERSE_DUTY_CYCLE);

// Coffee Machine Safety Parameters
#define HEATER_TIMEOUT 5000      // Heater auto-off if pump not used (ms)
#define NO_FLOW_TIMEOUT 1000     // Heater auto-off if no flow detected for this duration (ms)
#define POST_PUMP_COOLDOWN 1000  // Heater off delay after pump stops (ms)
#define QUEUE_SIZE 20            // Command queue capacity

// ==========================================================
// --- Global Variables & Objects ---
// ==========================================================

// VESC Objects and State (VESC1=Grinder/Duty, VESC2=Drum/RPM)
VescUart vesc1;                    // Grinder Motor (Duty Control)
VescUart vesc2;                    // Drum Motor (RPM Control)
float currentDuty1 = 0.0f;
float targetDuty1  = 0.0f;
float currentRpm2 = 0.0f;          // Current RPM for VESC2 (Drum) - used for ramping
float targetRpm2 = 0.0f;           // Target RPM for VESC2 (Drum)
uint32_t lastDutyStepTime = 0;
uint32_t lastRpmStepTime = 0;      // Timer for VESC2 RPM stepping

// Servo Objects
Servo servoA;
Servo servoB;
Servo servoC;
Servo servoD;

// Servo State Management Structure
struct ServoControlState {
  Servo& servoObject;             // Reference to the actual Servo object
  const int forwardSpeed;         // Forward speed for this specific servo
  const int reverseSpeed;         // Reverse speed for this specific servo
  bool isRunning;                 // Is the servo currently commanded to run?
  unsigned long stopTime;         // millis() value when the servo should stop completely
  unsigned long periodStartTime;  // millis() value when the current forward/reverse period started
  bool isForward;                 // Is the servo currently in the forward phase of the period?
  char id;                        // Identifier ('A', 'B', 'C', 'D')
};

// State instances for each servo
ServoControlState servoAState = { servoA, SERVO_A_FORWARD_SPEED, SERVO_A_REVERSE_SPEED, false, 0, 0, true, 'A' };
ServoControlState servoBState = { servoB, SERVO_B_FORWARD_SPEED, SERVO_B_REVERSE_SPEED, false, 0, 0, true, 'B' };
ServoControlState servoCState = { servoC, SERVO_C_FORWARD_SPEED, SERVO_C_REVERSE_SPEED, false, 0, 0, true, 'C' };
ServoControlState servoDState = { servoD, SERVO_D_FORWARD_SPEED, SERVO_D_REVERSE_SPEED, false, 0, 0, true, 'D' };

// Coffee Machine State & Command Queue
bool heaterActive = false;              
bool pumpUsedSinceHeaterOn = false;     
unsigned long heaterStartTime = 0;      
unsigned long generalDelayEndTime = 0;  // Time when 'D' command delay finishes

// --- State for No-Flow Safety Check ---
unsigned long lastPulseCheckCount = 0;  // Stores pulseCount during previous safety check
unsigned long lastNoPulseTime = 0;      // Stores millis() when heater was ON but no flow started

// Command structure and queue definitions
enum CommandType { CMD_R,
                   CMD_G,
                   CMD_P,
                   CMD_H,
                   CMD_S,
                   CMD_D,
                   CMD_INVALID };  
struct Command {
  CommandType type;
  float value1 = 0;  // R:RPM, G:Duty, P:Volume(mL), H:Power%, S:Calculated Duration(sec), D:Delay(ms) <-- S value updated
  float value2 = 0;  // P:Flow Rate(mL/s), S: Requested Grams <-- S value updated
  char id = ' ';     // S: Servo ID (A, B, C, D)
};
Command cmdQueue[QUEUE_SIZE];                       // Array to hold commands
int queueFront = 0, queueRear = 0, queueCount = 0;  // Queue pointers and count

// Serial Input Buffer
String serialInputBuffer = "";

// --- Function Prototypes ---

// NEW Pump Control Functions
void updateAdvancedWaterPump();                                                     // Encapsulates the main pump control logic loop
void resetFlowControlState();                                                       // Resets PID, volume tracking, etc. for a new dispense
void computeFlowPID(double input, double setpoint, double deltaTime_s);             // Calculates the PID output
void updateKalmanFilterFlow(double measured_ticks_per_second, double deltaTime_s);  // Runs Kalman filter prediction and update
double calculateTicksPerMilliliter(double flowRate_mL_s);                           // Calculates TPmL based on estimated flow rate

// Existing Functions
void updateServo(ServoControlState& state);
void checkSafetyFeatures();
void handleRoot();
void handleCommand();
void handleStatus();
void handleNotFound();
Command parseToken(const String& token);
int countValidCommandsInString(const String& input);
void processAndEnqueueCommands(const String& input);
char getCommandTypeChar(CommandType type);
void executeCommandFromQueue();
void updateVescControl();
void stepRpm2();


// ==========================================================
// --- Interrupt Service Routines (For Flow Rate) ---
// ==========================================================
void IRAM_ATTR flowISR() {
  pulseCount++; 
}

// ==========================================================
// --- Helper Functions ---
// ==========================================================

// --- VESC Ramping Helpers ---

// Gradually steps the current RPM towards the target RPM for VESC2
void stepRpm2() {
  float diff = targetRpm2 - currentRpm2;
  if (fabs(diff) <= RPM_STEP_SIZE) {
    currentRpm2 = targetRpm2;  // Snap to target if close enough
  } else {
    currentRpm2 += (diff > 0 ? RPM_STEP_SIZE : -RPM_STEP_SIZE);  
  }
}

// Gradually steps the current Duty signal to target Duty for VESC1
void stepDuty1() {
  float diff = targetDuty1 - currentDuty1;
  if (fabs(diff) <= DUTY_STEP_SIZE) {
    currentDuty1 = targetDuty1;
  } else {
    currentDuty1 += (diff > 0 ? DUTY_STEP_SIZE : -DUTY_STEP_SIZE);
  }
   currentDuty1 = constrain(currentDuty1, -0.12f, 0.12); // Ensure duty stays within bounds
}


// --- Command Processing Helpers ---
// Parses a single command token (e.g., "R-1000", "S-A-10.5") into a Command struct
Command parseToken(const String& token) {
  Command cmd;             // Create a command object
  cmd.type = CMD_INVALID;  // Default to invalid

  // Basic validation: must be at least 3 chars (e.g., R-0) and have '-' at index 1
  if (token.length() < 3 || token[1] != '-') {
    return cmd;
  }

  char cmdType = toupper(token[0]);    // Get command type (R, G, P, H, S, D)
  String params = token.substring(2);  // Extract parameters after "X-"

  // Parse based on command type
  switch (cmdType) {
    case 'R':  // R-<rpm> (Drum RPM)
      cmd.type = CMD_R;
      cmd.value1 = params.toFloat();
      break;
    case 'G':  // G-<amps> (Grinder Duty)
      cmd.type = CMD_G;
      cmd.value1 = params.toFloat();
      if (cmd.value1 < -0.12 || cmd.value1 > 0.12) {
        Serial.println("Warning: Grinder Duty " + String(cmd.value1) + " Duty out of range (-0.12 to 0.12). Clamping will occur.");
      }
      break;
    case 'P': // P-<volume>-<rate>
      {
        int dashIndex = params.indexOf('-');
        if (dashIndex != -1) {
          cmd.type = CMD_P;
          cmd.value1 = params.substring(0, dashIndex).toFloat();   // Volume (mL)
          cmd.value2 = params.substring(dashIndex + 1).toFloat();  // Rate (mL/s)
          if (cmd.value1 <= 0 || cmd.value2 <= 0) {
            Serial.println("Invalid P command values (volume and rate must be > 0). Token: " + token);
            cmd.type = CMD_INVALID;
          }
        } else {
          Serial.println("Invalid P command format (missing dash between volume and rate). Token: " + token);
          cmd.type = CMD_INVALID;
        }
      }
      break;
    case 'H':  // H-<power%>
      cmd.type = CMD_H;
      cmd.value1 = params.toFloat();
      if (cmd.value1 < 0 || cmd.value1 > 100) {
        Serial.println("Invalid H command value (must be 0-100). Token: " + token);
        cmd.type = CMD_INVALID;
      }
      break;
    case 'S': // S-<id>-<grams> 
      {
         int dashIndex = params.indexOf('-');
         // Check format: Dash must be at index 1 (e.g., "A-10.5") and string must continue after dash
         if (dashIndex == 1 && params.length() > dashIndex + 1) {
           cmd.id = toupper(params[0]); // Servo ID (A, B, C, D)
           float requestedGrams = params.substring(dashIndex + 1).toFloat(); // Get requested grams

           // Validate ID and requested grams
           if ((cmd.id >= 'A' && cmd.id <= 'D') && requestedGrams > 0 && SERVO_GRAMS_PER_SECOND > 0) {
              cmd.type = CMD_S;
              // Calculate required duration in seconds
              float durationSec = (requestedGrams / SERVO_GRAMS_PER_SECOND) + 1;
              cmd.value1 = durationSec;     
              cmd.value2 = requestedGrams;   
           } else {
              if (SERVO_GRAMS_PER_SECOND <= 0) {
                Serial.println("Error: SERVO_GRAMS_PER_SECOND calibration constant is not positive.");
              }
              Serial.println("Invalid S command values (ID A-D, grams > 0). Token: " + token);
              cmd.type = CMD_INVALID; // Mark invalid if validation fails
           }
         } else {
            Serial.println("Invalid S command format (expecting S-ID-grams, e.g., S-A-10.5). Token: " + token); // Updated help text
            cmd.type = CMD_INVALID; // Mark invalid if format is wrong
         }
      }
      break;
    case 'D':  // D-<time_ms>
      cmd.type = CMD_D;
      cmd.value1 = params.toFloat();
      if (cmd.value1 <= 0) {
        Serial.println("Invalid D command value (must be > 0 ms). Token: " + token);
        cmd.type = CMD_INVALID;
      }
      break;
    default:
      Serial.println("Unknown command type '" + String(cmdType) + "'. Token: " + token);
      break;
  }
  return cmd;
}

// Counts the number of valid command tokens within a space-separated string
int countValidCommandsInString(const String& input) {
  String currentToken;
  int validCount = 0;
  for (int i = 0; i < input.length(); i++) {
    if (input[i] == ' ' || i == input.length() - 1) {
      if (i == input.length() - 1 && input[i] != ' ') currentToken += input[i];
      currentToken.trim();
      if (currentToken.length() > 0) {
        if (parseToken(currentToken).type != CMD_INVALID) validCount++;
      }
      currentToken = "";
    } else {
      currentToken += input[i];
    }
  }
  return validCount;
}

// Parses a command string and adds *valid* commands to the queue.
void processAndEnqueueCommands(const String& input) {
  String currentToken;
  int cmdAddedCount = 0;
  for (int i = 0; i < input.length(); i++) {
    if (input[i] == ' ' || i == input.length() - 1) {
      if (i == input.length() - 1 && input[i] != ' ') currentToken += input[i];
      currentToken.trim();
      if (currentToken.length() > 0) {
        Command cmd = parseToken(currentToken);
        if (cmd.type != CMD_INVALID) {
          if (queueCount < QUEUE_SIZE) {
            cmdQueue[queueRear] = cmd;
            queueRear = (queueRear + 1) % QUEUE_SIZE;
            queueCount++;
            cmdAddedCount++;
          } else {
            Serial.println("ERROR: Queue full during enqueue.");
            break;
          }
        }
      }
      currentToken = "";
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

// Handles requests to the root URL ("/") - displays the control form
void handleRoot() {
  // Simple HTML form (Placeholder text updated for S command)
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
    <input type='text' id='cmd' name='cmd' size='50' placeholder='e.g., R-1000 G-2.5 P-50-2.0 H-75 S-A-12.2 D-1000'> <button type='submit'>Send Command</button> </form>

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
  if (!server.hasArg("cmd")) {
    server.send(400, "text/plain", "Bad Request: Missing 'cmd'.");
    return;
  }
  String input = server.arg("cmd");
  input.trim();
  Serial.println("Received Web Command: " + input);
  if (input.length() == 0) {
    server.send(400, "text/plain", "Bad Request: Empty command.");
    return;
  }
  int requiredSlots = countValidCommandsInString(input);
  int availableSlots = QUEUE_SIZE - queueCount;
  if (requiredSlots == 0) {
    server.send(400, "text/plain", "No valid commands found.");
    Serial.println("Web command rejected: No valid commands.");
  } else if (requiredSlots > availableSlots) {
    String msg = "Queue full. Required: " + String(requiredSlots) + ", Available: " + String(availableSlots);
    server.send(503, "text/plain", msg);
    Serial.println(msg);
  } else {
    processAndEnqueueCommands(input);
    String msg = String(requiredSlots) + " command(s) accepted. Queue: " + String(queueCount) + "/" + String(QUEUE_SIZE);
    server.send(200, "text/plain", msg);
  }
}

// Handles GET requests to "/status" - provides current machine status
void handleStatus() {
  String status = "--- VESC Status ---\n";
  // VESC1 = Grinder (Current), VESC2 = Drum (RPM)
  status += "Grinder (Duty): Target=" + String(targetDuty1, 2) + ", Current=" + String(currentDuty1, 2) + "\n";
  status += "Drum (RPM): Target=" + String(targetRpm2) + ", Current=" + String(currentRpm2, 0) + "\n";
  status += "--- Water Pump Status (Kalman/PID) ---\n";
  status += "State: " + String(currentFlowState == FLOW_DISPENSING ? "DISPENSING" : "IDLE") + "\n";
  status += "Target: " + String(targetVolume_mL, 1) + " mL @ " + String(targetFlowRate_mL_s, 2) + " mL/s\n";
  status += "Current: " + String(totalVolumeDispensed_mL, 1) + " mL / " + String(x_hat_flow, 2) + " mL/s (Est. KF)\n";
  noInterrupts();
  status += "Pulses This Dispense: " + String(totalPulseCountDispense) + "\n";
  interrupts();
  status += "PWM Command: " + String((int)round(lastPidOutput_flow)) + "\n";
  status += "--- Heater Status ---\n";
  status += "State: " + String(heaterActive ? "ON" : "OFF") + "\n";
  status += "--- Servo Status ---\n";
  ServoControlState* states[] = { &servoAState, &servoBState, &servoCState, &servoDState };
  unsigned long now = millis();
  for (int i = 0; i < 4; ++i) {
    status += String(states[i]->id) + ": ";
    if (states[i]->isRunning) {
      status += String(states[i]->isForward ? "FWD" : "REV");
      status += " (Speed " + String(states[i]->isForward ? states[i]->forwardSpeed : states[i]->reverseSpeed) + ")";
      unsigned long remaining_ms = (states[i]->stopTime > now) ? (states[i]->stopTime - now) : 0;
      // Display remaining time based on the calculated duration
      status += " Rem: " + String(remaining_ms / 1000.0, 1) + "s";
    } else {
      status += "STOPPED (Speed " + String(SERVO_STOP_SPEED) + ")";
    }
    status += " | ";
  }
  if (status.endsWith(" | ")) { status = status.substring(0, status.length() - 3); }
  status += "\n--- System Status ---\n";
  status += "Command Queue: " + String(queueCount) + "/" + String(QUEUE_SIZE) + "\n";
  status += "Delay Active: " + String(millis() < generalDelayEndTime ? "YES (" + String((generalDelayEndTime - millis()) / 1000.0, 1) + "s left)" : "NO") + "\n";
  status += "Uptime: " + String(millis() / 1000) + " s\n";

  server.send(200, "text/plain", status);
}

// Handles requests to URLs not matching defined routes
void handleNotFound() {
  server.send(404, "text/plain", "Not Found.");
}
#endif  // WEB_MODE

// ==========================================================
// --- Pump Control Functions ---
// ==========================================================

// Resets PID, Kalman state, and volume tracking for a new dispense operation
void resetFlowControlState() {
  // Reset PID state variables
  integralTerm_flow = 0.0;   // Clear accumulated integral error
  lastError_flow = 0.0;      // Clear previous error
  pidOutput_flow = 0.0;      // Reset PID output
  lastPidOutput_flow = 0.0;  // Reset last commanded PWM (used for Kalman)

  // Reset volume and pulse tracking for the dispense
  totalVolumeDispensed_mL = 0.0;
  totalPulseCountDispense = 0;

  if (currentFlowState == FLOW_IDLE) {
    ledcWrite(PUMP_LEDC_CHANNEL, 0);
  }
}

// Calculates PID + Feedforward output for the pump based on Kalman-estimated flow rate and setpoint
void computeFlowPID(double input, double setpoint, double deltaTime_s) {
  if (deltaTime_s <= 0) return;

  // --- PID Component ---
  double error = setpoint - input;
  double pTerm = Kp_flow * error;
  double derivative = (error - lastError_flow) / deltaTime_s;
  double dTerm = Kd_flow * derivative;
  double potentialIntegralStep = Ki_flow * error * deltaTime_s;
  double currentOutputNoIntegralStep = overallGain_flow * (pTerm + integralTerm_flow + dTerm);
  bool outputSaturated = (currentOutputNoIntegralStep >= 255.0 || currentOutputNoIntegralStep <= 0.0);
  if (!outputSaturated || (error * integralTerm_flow < 0)) {
    integralTerm_flow += potentialIntegralStep;
  }
  double pidComponent = overallGain_flow * (pTerm + integralTerm_flow + dTerm);

  // --- Feedforward Component ---
  double ffComponent = FF_SLOPE * setpoint + FF_INTERCEPT;

  // --- Combine PID and Feedforward ---
  double combinedOutput = pidComponent + ffComponent; 

  lastError_flow = error; // Store error for next derivative calculation

  // Set the global output, constrained to PWM range [0, 255]
  pidOutput_flow = constrain(combinedOutput, 0.0, 255.0);
}

// Updates the Kalman filter estimate of the flow rate (mL/s)
void updateKalmanFilterFlow(double measured_ticks_per_second, double deltaTime_s) {

  // --- Prediction Step ---
  double x_hat_minus_ff = (lastPidOutput_flow - FF_INTERCEPT) / FF_SLOPE; // Prediction using inverted FF
  double x_hat_minus = x_hat_flow; 
  x_hat_minus = constrain(x_hat_minus, MIN_FLOW_RATE, MAX_FLOW_RATE); // Constrain prediction

  double P_minus = P_flow + Q_flow;

  // --- Update Step ---
  double TPmL_predicted = calculateTicksPerMilliliter(x_hat_minus);
  if (TPmL_predicted <= 0) {
    Serial.println("Warning: Kalman TPmL prediction failed. Using prediction only.");
    x_hat_flow = x_hat_minus;
    P_flow = P_minus;
    return;
  }
  double H = TPmL_predicted;
  double h_x = x_hat_minus * H;
  double y = measured_ticks_per_second - h_x;
  double S = H * P_minus * H + R_flow;
  double K = (S == 0) ? 0 : (P_minus * H / S);
  x_hat_flow = x_hat_minus + K * y;
  P_flow = (1.0 - K * H) * P_minus;
  x_hat_flow = constrain(x_hat_flow, MIN_FLOW_RATE, MAX_FLOW_RATE);
  if (P_flow < 1e-6) P_flow = 1e-6;
}

// Calculates Ticks per Milliliter (TPmL) using the direct quadratic equation.
double calculateTicksPerMilliliter(double flowRate_mL_s) {
  if (flowRate_mL_s < MIN_FLOW_RATE || flowRate_mL_s > MAX_FLOW_RATE) {
    return -1.0;
  }
  double tpmL = (TPmL_A * flowRate_mL_s * flowRate_mL_s) + (TPmL_B * flowRate_mL_s) + TPmL_C;
  if (tpmL > 0) {
    return tpmL;
  } else {
    return -2.0;
  }
}

// ==========================================================
// --- Core Logic Functions ---
// ==========================================================

// Helper to get the character for the command type (for printing)
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

// Executes the next command from the queue if available and no delay is active
void executeCommandFromQueue() {
  if (queueCount > 0 && millis() >= generalDelayEndTime) {
    Command cmd = cmdQueue[queueFront];
    queueFront = (queueFront + 1) % QUEUE_SIZE;
    queueCount--;
    Serial.print("Executing Cmd: ");
    Serial.print(getCommandTypeChar(cmd.type));
    Serial.print("-");
    switch (cmd.type) {
      case CMD_R:
        Serial.println(String(cmd.value1));
        targetRpm2 = cmd.value1;
        break;

      case CMD_G:
        Serial.println(String(cmd.value1, 2));
        if (cmd.value1 < -0.12 || cmd.value1 > 0.12) {
          Serial.println("Warning: Duty cycle " + String(cmd.value1) + " out of range (-0.12 to 0.12). Clamping may occur.");
        }
        break;

      case CMD_P:
        {
          Serial.println(String(cmd.value1, 1) + "mL-" + String(cmd.value2, 2) + "mL/s");
          double requestedVol = cmd.value1;
          double requestedFlow = cmd.value2;
          if (requestedVol <= 0) { Serial.println("  Error: Volume must be positive."); break; }
          if (requestedFlow < MIN_FLOW_RATE || requestedFlow > MAX_FLOW_RATE) {
            Serial.print("  Error: Requested flow rate ("); Serial.print(requestedFlow, 2);
            Serial.print(") outside valid range ["); Serial.print(MIN_FLOW_RATE, 1); Serial.print(" - ");
            Serial.print(MAX_FLOW_RATE, 1); Serial.println("] mL/s."); break;
          }
          if (currentFlowState == FLOW_IDLE) {
            targetVolume_mL = requestedVol; targetFlowRate_mL_s = requestedFlow;
            resetFlowControlState();
            noInterrupts(); pulseCount = 0; interrupts();
            currentFlowState = FLOW_DISPENSING; pumpUsedSinceHeaterOn = true;
            Serial.println("  Starting dispense (Advanced Control)...");
          } else { Serial.println("  Warning: Pump already in FLOW_DISPENSING state. Command ignored."); }
        }
        break;

      case CMD_H:
        {
          Serial.println(String(cmd.value1));
          int heaterDuty = map(constrain((int)cmd.value1, 0, 100), 0, 100, 0, 255);
          ledcWrite(HEATER_LEDC_CHANNEL, heaterDuty);
          heaterActive = (heaterDuty > 0);
          if (heaterActive) {
            heaterStartTime = millis(); pumpUsedSinceHeaterOn = false;
            noInterrupts(); lastPulseCheckCount = pulseCount; interrupts();
            lastNoPulseTime = 0;
            Serial.println("  Heater ON");
          } else { Serial.println("  Heater OFF"); lastNoPulseTime = 0; }
        }
        break;

      case CMD_S:
        {
            // value1 holds calculated duration in seconds, value2 holds requested grams
            float calculatedDurationSeconds = cmd.value1;
            float requestedGrams = cmd.value2;
            unsigned long durationMillis = (unsigned long)(calculatedDurationSeconds * 1000.0f);
            unsigned long currentTime = millis();
            ServoControlState* stateToUpdate = nullptr;

            // Print information about the request and calculated time
            Serial.print(cmd.id); Serial.print("-"); Serial.print(String(requestedGrams, 2) + "g");
            Serial.println(" -> Calculated Time: " + String(calculatedDurationSeconds, 2) + "s");

            switch (cmd.id) {
                case 'A': stateToUpdate = &servoAState; break;
                case 'B': stateToUpdate = &servoBState; break;
                case 'C': stateToUpdate = &servoCState; break;
                case 'D': stateToUpdate = &servoDState; break;
                default: Serial.println("  Error: Invalid Servo ID!"); break;
            }

            if (stateToUpdate != nullptr) {
                stateToUpdate->isRunning = true;
                stateToUpdate->stopTime = currentTime + durationMillis; // Use calculated duration
                stateToUpdate->periodStartTime = currentTime;
                stateToUpdate->isForward = true;
                stateToUpdate->servoObject.write(stateToUpdate->forwardSpeed);
                Serial.print("  Servo "); Serial.print(cmd.id);
                Serial.print(" starting periodic run for "); Serial.print(calculatedDurationSeconds, 2); Serial.println("s");
                Serial.print("      -> Starting FORWARD (Speed: "); Serial.print(stateToUpdate->forwardSpeed); Serial.println(")");
            }
        }
        break;

      case CMD_D:
        Serial.println(String(cmd.value1, 0) + "ms");
        generalDelayEndTime = millis() + (unsigned long)cmd.value1;
        Serial.println("  Delaying execution...");
        break;

      default: Serial.println(" ERROR: Executing invalid command type!"); break;
    }
  }
}

// Updates VESC control signals
void updateVescControl() {
  uint32_t now_us = micros();
  if ((now_us - lastDutyStepTime) >= DUTY_STEP_INTERVAL_US) {
    stepDuty1();
    vesc1.setCurrent(currentDuty1);
    lastDutyStepTime = now_us;
  }
  if ((now_us - lastRpmStepTime) >= RPM_STEP_INTERVAL_US) {
    stepRpm2();
    vesc2.setRPM((int32_t)currentRpm2);
    lastRpmStepTime = now_us;
  }
}

// Updates the state of a single servo
void updateServo(ServoControlState& state) {
  if (!state.isRunning) return;
  unsigned long currentTime = millis();
  if (currentTime >= state.stopTime) {
    state.servoObject.write(SERVO_STOP_SPEED);
    state.isRunning = false;
    Serial.print("Servo "); Serial.print(state.id);
    Serial.println(" stopped (Total time elapsed). Speed: " + String(SERVO_STOP_SPEED));
    return;
  }
  unsigned long timeInPeriod = currentTime - state.periodStartTime;
  if (state.isForward) {
    if (timeInPeriod >= FORWARD_DURATION_MS) {
      state.servoObject.write(state.reverseSpeed);
      state.isForward = false;
      Serial.print("Servo "); Serial.print(state.id);
      Serial.print(" switching to REVERSE (Speed: "); Serial.print(state.reverseSpeed); Serial.println(")");
    }
  } else {
    if (timeInPeriod >= SERVO_PERIOD_MS) {
      state.servoObject.write(state.forwardSpeed);
      state.isForward = true;
      state.periodStartTime = currentTime;
      Serial.print("Servo "); Serial.print(state.id);
      Serial.print(" switching to FORWARD (Speed: "); Serial.print(state.forwardSpeed); Serial.println(")");
    }
  }
}


// Checks for safety conditions
void checkSafetyFeatures() {
  unsigned long currentTime = millis();
  // Heater Timeout
  if (heaterActive && !pumpUsedSinceHeaterOn && (currentTime - heaterStartTime > HEATER_TIMEOUT)) {
    Serial.println("Safety Trigger: Heater timed out (pump not used). Turning OFF.");
    ledcWrite(HEATER_LEDC_CHANNEL, 0); heaterActive = false; lastNoPulseTime = 0;
  }
  // No-Flow Timeout
  if (heaterActive) {
    unsigned long currentPulses; noInterrupts(); currentPulses = pulseCount; interrupts();
    if (currentPulses == lastPulseCheckCount) {
      if (lastNoPulseTime == 0) { lastNoPulseTime = currentTime; }
      else if (currentTime - lastNoPulseTime > NO_FLOW_TIMEOUT) {
        Serial.println("Safety Trigger: Heater ON but no flow detected for > " + String(NO_FLOW_TIMEOUT) + "ms. Turning OFF.");
        ledcWrite(HEATER_LEDC_CHANNEL, 0); heaterActive = false; lastNoPulseTime = 0;
      }
    } else { lastNoPulseTime = 0; }
    lastPulseCheckCount = currentPulses;
  } else { lastNoPulseTime = 0; }
  // Heater Cooldown after Pump
  if (currentFlowState == FLOW_IDLE && heaterActive && generalDelayEndTime > 0 && currentTime >= generalDelayEndTime) {
    Serial.println("Heater post-pump cooldown finished (based on delay timer). Turning OFF.");
    ledcWrite(HEATER_LEDC_CHANNEL, 0); heaterActive = false; lastNoPulseTime = 0;
    generalDelayEndTime = 0;
  }
}

// ==========================================================
// --- Water Pump Update Function ---
// ==========================================================
void updateAdvancedWaterPump() {
  unsigned long currentTime = millis();
  if (currentTime - lastMeasurementTime >= SAMPLE_TIME_MS) {
    unsigned long intervalStartTime = lastMeasurementTime;
    lastMeasurementTime = currentTime;
    double deltaTime_s = (currentTime - intervalStartTime) / 1000.0;

    // --- Read Sensor Data ---
    unsigned long currentPulseReading; noInterrupts(); currentPulseReading = pulseCount; pulseCount = 0; interrupts();

    // --- Calculate Measured Ticks Per Second ---
    double measured_ticks_per_second = (deltaTime_s > 0.0001) ? ((double)currentPulseReading / deltaTime_s) : 0.0;

    // --- Update Kalman Filter ---
    updateKalmanFilterFlow(measured_ticks_per_second, deltaTime_s);
    pidInput_flow = x_hat_flow;

    // --- Update Total Volume Dispensed ---
    if (currentFlowState == FLOW_DISPENSING && currentPulseReading > 0) {
      double currentTPmL = calculateTicksPerMilliliter(x_hat_flow);
      if (currentTPmL > 0) { totalVolumeDispensed_mL += (double)currentPulseReading / currentTPmL; }
      else { Serial.println("Warning: Invalid TPmL for volume calculation."); }
      totalPulseCountDispense += currentPulseReading;
    }

    // --- PID Control Calculation ---
    if (currentFlowState == FLOW_DISPENSING) {
      pidSetpoint_flow = targetFlowRate_mL_s;
      computeFlowPID(pidInput_flow, pidSetpoint_flow, deltaTime_s);
    } else { pidOutput_flow = 0.0; integralTerm_flow = 0.0; }

    // --- Actuate Pump Motor ---
    int pwmCommand = constrain((int)round(pidOutput_flow), 0, 255);
    ledcWrite(PUMP_LEDC_CHANNEL, pwmCommand);
    lastPidOutput_flow = (double)pwmCommand;

    // --- Check for Dispensing Completion ---
    if (currentFlowState == FLOW_DISPENSING && totalVolumeDispensed_mL >= targetVolume_mL) {
      currentFlowState = FLOW_IDLE; ledcWrite(PUMP_LEDC_CHANNEL, 0);
      pidOutput_flow = 0.0; lastPidOutput_flow = 0.0;
      Serial.println("\n----------------------------------------");
      Serial.print("Dispensing Complete!"); Serial.print(" Target: "); Serial.print(targetVolume_mL, 2);
      Serial.print(" mL, Actual: "); Serial.print(totalVolumeDispensed_mL, 2);
      Serial.print(" mL, Total Ticks: "); Serial.println(totalPulseCountDispense);
      Serial.println("System IDLE."); Serial.println("----------------------------------------");
      if (heaterActive) { generalDelayEndTime = millis() + POST_PUMP_COOLDOWN; Serial.println("Heater cooldown delay started (" + String(POST_PUMP_COOLDOWN) + "ms)."); }
    }

    // --- Serial Debug Output ---
    if (currentFlowState == FLOW_DISPENSING) {
      Serial.print("T: "); Serial.print(currentTime / 1000.0, 1); Serial.print("s | Tgt: "); Serial.print(pidSetpoint_flow, 2);
      Serial.print(" | Est(KF): "); Serial.print(pidInput_flow, 2); Serial.print(" | PWM: "); Serial.print(pwmCommand);
      Serial.print(" | Vol: "); Serial.print(totalVolumeDispensed_mL, 2); Serial.print("/"); Serial.print(targetVolume_mL, 2);
      Serial.print("mL | Ticks/s: "); Serial.print(measured_ticks_per_second, 1); Serial.println();
    }
  }
}


// ==========================================================
// --- ESP32 Setup ---
// ==========================================================
void setup() {
  Serial.begin(SERIAL_BAUD);
  while (!Serial && millis() < 2000);
  Serial.println("\n\n--- Combined Control System Initializing ---");
  Serial.println("*** Flow control using Kalman Filter & PID (Encapsulated) ***");
  Serial.println("*** ASSUMING Liquid Density ~1 g/mL for flow calculations (TPmL/FF coeffs) ***");

  pinMode(OE_PIN, OUTPUT); digitalWrite(OE_PIN, HIGH);
  Serial.println("Logic Level Shifter Enabled (Pin " + String(OE_PIN) + ")");

  Serial1.begin(SERIAL_BAUD, SERIAL_8N1, VESC1_RX_PIN, VESC1_TX_PIN);
  Serial2.begin(SERIAL_BAUD, SERIAL_8N1, VESC2_RX_PIN, VESC2_TX_PIN);
  vesc1.setSerialPort(&Serial1); vesc2.setSerialPort(&Serial2);
  Serial.println("VESC UART Ports Initialized (VESC1=Grinder Current, VESC2=Drum RPM).");

  pinMode(PUMP_PWM_PIN, OUTPUT); ledcSetup(PUMP_LEDC_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(PUMP_PWM_PIN, PUMP_LEDC_CHANNEL); ledcWrite(PUMP_LEDC_CHANNEL, 0);
  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP); attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), flowISR, RISING);
  Serial.println("Water Pump & Flow Sensor Initialized (using Kalman/PID control).");

  pinMode(HEATER_PIN, OUTPUT); ledcSetup(HEATER_LEDC_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(HEATER_PIN, HEATER_LEDC_CHANNEL); ledcWrite(HEATER_LEDC_CHANNEL, 0);
  Serial.println("Heater Initialized.");

  ESP32PWM::allocateTimer(0); ESP32PWM::allocateTimer(1); ESP32PWM::allocateTimer(2); ESP32PWM::allocateTimer(3);
  servoA.attach(SERVO_PIN_A); servoB.attach(SERVO_PIN_B); servoC.attach(SERVO_PIN_C); servoD.attach(SERVO_PIN_D);
  servoA.write(SERVO_STOP_SPEED); servoB.write(SERVO_STOP_SPEED); servoC.write(SERVO_STOP_SPEED); servoD.write(SERVO_STOP_SPEED);
  Serial.println("Servos Initialized & Stopped (Speed: " + String(SERVO_STOP_SPEED) + ").");

  resetFlowControlState();
  lastMeasurementTime = millis();

  Serial.println("Using Direct TPmL Equation: TPmL = A*Flow^2 + B*Flow + C");
  Serial.print("  A="); Serial.print(TPmL_A, 4); Serial.print(", B="); Serial.print(TPmL_B, 4); Serial.print(", C="); Serial.println(TPmL_C, 4);
  Serial.println("PID Gains: Kp, Ki, Kd set relative weights, overallGain sets strength.");
  Serial.print("  Kp="); Serial.print(Kp_flow); Serial.print(", Ki="); Serial.print(Ki_flow); Serial.print(", Kd="); Serial.print(Kd_flow); Serial.print(", overallGain="); Serial.println(overallGain_flow);
  Serial.print("Kalman Params: Q="); Serial.print(Q_flow); Serial.print(", R="); Serial.println(R_flow);


#ifdef WEB_MODE
  Serial.print("Connecting to WiFi: "); Serial.println(ssid);
  WiFi.begin(ssid, password);
  int wifi_retries = 0;
  while (WiFi.status() != WL_CONNECTED && wifi_retries < 20) { delay(500); Serial.print("."); wifi_retries++; }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected!"); Serial.print("IP Address: "); Serial.println(WiFi.localIP());
    server.on("/", HTTP_GET, handleRoot); server.on("/command", HTTP_POST, handleCommand);
    server.on("/status", HTTP_GET, handleStatus); server.onNotFound(handleNotFound);
    server.begin(); Serial.println("Web Server Started.");
  } else { Serial.println("\nWiFi Connection Failed!"); }
#endif

  Serial.println("\n--- System Ready ---");
  Serial.println("Format examples:");
  Serial.println("  R-<rpm>           (Drum RPM, e.g., R-3000)");
  Serial.println("  G-<duty>          (Grinder Duty -0.12-0.12, e.g., G-0.10)");
  Serial.println("  P-<vol>-<rate>    (Pump Volume[mL] & Rate[mL/s], e.g., P-100-2.5)");
  Serial.println("                    (Flow rate must be within [" + String(MIN_FLOW_RATE, 1) + " - " + String(MAX_FLOW_RATE, 1) + "] mL/s)");
  Serial.println("  H-<power%>        (Heater Power 0-100%, e.g., H-80)");
  Serial.println("  S-<id>-<grams>    (Servo ID [A-D] dispense grams, e.g., S-A-12.2)"); 
  Serial.println("                    (Calculates run time based on " + String(SERVO_GRAMS_PER_SECOND, 2) + " g/s rate)"); 
  Serial.println("                    (Uses periodic motion: " + String(SERVO_PERIOD_SECONDS) + "s period, " + String(FORWARD_DUTY_CYCLE * 100, 0) + "% Fwd / " + String(REVERSE_DUTY_CYCLE * 100, 0) + "% Rev)");
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
#endif

#if defined(SERIAL_MODE) || !defined(WEB_MODE)
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      serialInputBuffer.trim();
      if (serialInputBuffer.length() > 0) {
        Serial.println("Received Serial Command: " + serialInputBuffer);
        int requiredSlots = countValidCommandsInString(serialInputBuffer);
        int availableSlots = QUEUE_SIZE - queueCount;
        if (requiredSlots == 0) { Serial.println("No valid commands found in input."); }
        else if (requiredSlots > availableSlots) { Serial.println("ERROR: Queue full. Required: " + String(requiredSlots) + ", Available: " + String(availableSlots) + ". Command rejected."); }
        else { processAndEnqueueCommands(serialInputBuffer); }
      }
      serialInputBuffer = "";
    } else if (isprint(c) && serialInputBuffer.length() < 200) { serialInputBuffer += c; }
  }
#endif

  updateVescControl();
  updateAdvancedWaterPump();
  updateServo(servoAState);
  updateServo(servoBState);
  updateServo(servoCState);
  updateServo(servoDState);
  executeCommandFromQueue();
  checkSafetyFeatures();

  yield();
}
// End of loop()
// S-C-30 D-30000 R-3600 D-3000 H-50 P-80-3 R-20000 D-5000
