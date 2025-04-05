#include <Arduino.h>
#include <math.h> // For pow() function

// --- Pin assignments ---
static const int PUMP_PWM_PIN    = 16; // L298N IN1 or ESP32 GPIO
static const int FLOW_SENSOR_PIN = 10;  // Flow sensor output (ensure correct voltage level)
static const int OE_PIN          = 8;  // Optional: L298N output enable (active HIGH) or logic level shifter enable

// --- Flow Sensor Calibration ---
// Ticks/mL = -0.0792 * (FlowRate)^2 + 1.0238 * (FlowRate) + 1.2755
// FlowRate (mL/s) = 0.0343 * Duty - 1.0155  => Duty = (FlowRate + 1.0155) / 0.0343

// --- Control Parameters ---
float targetVolumeML = 0.0;
float targetFlowRateMLPS = 0.0; // mL per second
bool dispensingActive = false;

// --- Measurement Variables ---
volatile unsigned long pulseCount = 0; // Updated by ISR
unsigned long lastPulseCount = 0;
float dispensedVolumeML = 0.0;
float currentFlowRateMLPS = 0.0;
unsigned long lastFlowCalcTime = 0;
const unsigned long flowCalcInterval = 100; // Calculate flow rate every 100 ms

// --- PID Controller Variables ---
float kp = 15.0;   // Proportional gain (NEEDS TUNING)
float ki = 30.0;   // Integral gain     (NEEDS TUNING)
float kd = 0.5;   // Derivative gain   (NEEDS TUNING)

float pidError = 0.0;
float lastError = 0.0;
float integralError = 0.0;
float derivativeError = 0.0;
float pidOutput = 0.0; // PID contribution to duty cycle

unsigned long lastControlTime = 0;
const unsigned long controlInterval = 50; // Run PID controller every 50 ms
float maxIntegral = 100.0; // Anti-windup limit for integral term

// --- Feedforward Variables ---
int feedforwardDuty = 0;

// --- Timing & State ---
unsigned long dispenseStartTime = 0;

// --- Interrupt Service Routine ---
// IRAM_ATTR is important for ESP32 to place ISR in RAM for speed
void IRAM_ATTR flowISR() {
  pulseCount++;
}

// --- Helper Function: Calculate Ticks per mL based on current flow rate ---
float getTicksPerML(float flowRate) {
  // Apply the calibration curve: Ticks/mL = -0.0792x^2 + 1.0238x + 1.2755
  // where x is flowRate in mL/s
  float ticks = -0.0792 * pow(flowRate, 2) + 1.0238 * flowRate + 1.2755;
  // Prevent division by zero or nonsensical values
  if (ticks <= 0.1) { // Use a small positive floor value
      // If calculated ticks is too low, it might mean flow rate is near zero
      // or the model isn't accurate here. Return a reasonable minimum?
      // Or, maybe use the value calculated at the *target* flow rate as a fallback?
      // Let's recalculate using the target as a rough estimate if current is ~0
      if (flowRate < 0.1 && targetFlowRateMLPS > 0.1) {
          ticks = -0.0792 * pow(targetFlowRateMLPS, 2) + 1.0238 * targetFlowRateMLPS + 1.2755;
          if (ticks <= 0.1) return 1.0; // Absolute fallback
          return ticks;
      }
      return 1.0; // Default fallback if calculation is non-positive
  }
  return ticks;
}

// --- Helper Function: Calculate Feedforward Duty based on target flow rate ---
int calculateFeedforwardDuty(float targetRate) {
  // Invert the flow rate vs duty equation: Duty = (FlowRate + 1.0155) / 0.0343
  if (targetRate <= 0) return 0; // Don't calculate for zero or negative flow
  float dutyFloat = (targetRate + 1.0155) / 0.0343;
  return constrain((int)round(dutyFloat), 0, 255); // Round and constrain
}

// --- Helper Function: Parse Input Command ---
bool parseInput(String input) {
  input.trim();
  input.toUpperCase(); // Make matching easier (V and F)

  int vIndex = input.indexOf('V');
  int fIndex = input.indexOf("-F");

  if (vIndex == 0 && fIndex > vIndex) {
    String volString = input.substring(vIndex + 1, fIndex);
    String rateString = input.substring(fIndex + 2); // Skip "-F"

    targetVolumeML = volString.toFloat();
    targetFlowRateMLPS = rateString.toFloat();

    if (targetVolumeML > 0 && targetFlowRateMLPS > 0) {
      Serial.print("Received command: Dispense ");
      Serial.print(targetVolumeML);
      Serial.print(" mL at ");
      Serial.print(targetFlowRateMLPS);
      Serial.println(" mL/s");
      return true; // Command parsed successfully
    } else {
      Serial.println("Error: Invalid volume or flow rate values.");
      return false;
    }
  }
  Serial.println("Error: Invalid command format. Use V<volume>-F<rate>");
  return false; // Command format invalid
}


// --- Setup ---
void setup() {
  Serial.begin(115200);
  while (!Serial); // Wait for Serial connection (optional)

  // --- Pin Setup ---
  pinMode(PUMP_PWM_PIN, OUTPUT);
  
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH); // Enable output (adjust logic if needed)

  // --- PWM Setup (LEDC for ESP32) ---
  // channel = 0, freq = 1000 Hz, resolution = 8 bits (0-255)
  ledcSetup(0, 1000, 8);
  ledcAttachPin(PUMP_PWM_PIN, 0);
  ledcWrite(0, 0); // Ensure pump is off initially

  // --- Flow Sensor Interrupt Setup ---
  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP); // Use INPUT if external pull-up exists
  attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), flowISR, RISING);

  Serial.println("\n--- Flow Control System Ready ---");
  Serial.println("Enter command in format: V<volume>-F<rate>");
  Serial.println("Example: V100-F2.2 (Dispense 100mL at 2.2 mL/s)");
  Serial.println("---------------------------------");
}

// --- Main Loop ---
void loop() {

  // --- Check for Serial Input ---
  if (Serial.available() > 0 && !dispensingActive) {
    String input = Serial.readStringUntil('\n');
    if (parseInput(input)) {
      // Start dispensing process
      dispensedVolumeML = 0.0;
      pulseCount = 0; // Reset total pulse count for this dispense
      lastPulseCount = 0;
      currentFlowRateMLPS = 0.0; // Reset current flow rate
      pidError = 0.0;
      lastError = 0.0;
      integralError = 0.0;
      derivativeError = 0.0;
      pidOutput = 0.0;
      feedforwardDuty = calculateFeedforwardDuty(targetFlowRateMLPS); // Calculate initial FF duty

      dispenseStartTime = millis();
      lastFlowCalcTime = dispenseStartTime;
      lastControlTime = dispenseStartTime;
      dispensingActive = true;

      Serial.print("Starting dispense. Target: ");
      Serial.print(targetVolumeML);
      Serial.print(" mL at ");
      Serial.print(targetFlowRateMLPS);
      Serial.print(" mL/s. Feedforward Duty: ");
      Serial.println(feedforwardDuty);
      Serial.println("Time(ms), TargetRate(mL/s), CurrentRate(mL/s), Dispensed(mL), FF Duty, PID Out, Total Duty"); // Header for CSV-like output

      // Apply initial duty (mostly feedforward)
      ledcWrite(0, feedforwardDuty);
    }
  }

  // --- Dispensing Logic ---
  if (dispensingActive) {
    unsigned long currentTime = millis();

    // --- Flow Rate Calculation Task (Runs periodically) ---
    if (currentTime - lastFlowCalcTime >= flowCalcInterval) {
      // Safely read volatile pulseCount
      noInterrupts(); // Disable interrupts briefly to read volatile var
      unsigned long currentPulses = pulseCount;
      interrupts(); // Re-enable interrupts

      unsigned long deltaPulses = currentPulses - lastPulseCount;
      float deltaTimeSeconds = (currentTime - lastFlowCalcTime) / 1000.0;
      lastFlowCalcTime = currentTime; // Update time for next interval
      lastPulseCount = currentPulses; // Update count for next interval

      if (deltaTimeSeconds > 0) {
          // Calculate Pulses Per Second (PPS)
          float pps = (float)deltaPulses / deltaTimeSeconds;

          // Estimate Ticks/mL based on the *previous* measured flow rate
          // This is an approximation, as Ticks/mL changes with flow rate
          float ticksPerML_est = getTicksPerML(currentFlowRateMLPS > 0.05 ? currentFlowRateMLPS : targetFlowRateMLPS); // Use target if current is near zero

          // Calculate current flow rate (mL/s)
          if (ticksPerML_est > 0.1) { // Avoid division by zero / small numbers
              currentFlowRateMLPS = pps / ticksPerML_est;
          } else {
              currentFlowRateMLPS = 0.0; // Assume zero flow if ticks/mL is invalid
          }

          // Update total dispensed volume using the most recent Ticks/mL estimation
          if (ticksPerML_est > 0.1) {
              dispensedVolumeML += (float)deltaPulses / ticksPerML_est;
          }
      } else {
           // Very short interval, skip calculation this cycle or assume previous rate?
           // For simplicity, we can just let the next cycle catch up.
      }
    }

    // --- PID Control Task (Runs periodically) ---
    if (currentTime - lastControlTime >= controlInterval) {
        float dt = (currentTime - lastControlTime) / 1000.0; // Delta time in seconds
        lastControlTime = currentTime;

        if (dt > 0) { // Avoid division by zero if loop runs extremely fast
            // Calculate Error
            pidError = targetFlowRateMLPS - currentFlowRateMLPS;

            // Calculate Integral (with anti-windup)
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
            ledcWrite(0, totalDuty);

            // --- Print Status (Optional - can slow things down) ---
            Serial.print(currentTime - dispenseStartTime); Serial.print(",");
            Serial.print(targetFlowRateMLPS, 3); Serial.print(",");
            Serial.print(currentFlowRateMLPS, 3); Serial.print(",");
            Serial.print(dispensedVolumeML, 2); Serial.print(",");
            Serial.print(feedforwardDuty); Serial.print(",");
            Serial.print(pidOutput, 2); Serial.print(",");
            Serial.println(totalDuty);

        } // end if dt > 0
    } // end PID control task timing check

    // --- Check Stop Condition ---
    if (dispensedVolumeML >= targetVolumeML) {
      ledcWrite(0, 0); // Stop the pump
      dispensingActive = false;

      unsigned long duration = millis() - dispenseStartTime;
      Serial.println("\n--- Dispense Complete ---");
      Serial.print("Target Volume: "); Serial.print(targetVolumeML, 2); Serial.println(" mL");
      Serial.print("Actual Volume: "); Serial.print(dispensedVolumeML, 2); Serial.println(" mL");
      Serial.print("Target Flow Rate: "); Serial.print(targetFlowRateMLPS, 2); Serial.println(" mL/s");
      // Optional: Calculate average flow rate
      if (duration > 0) {
        float avgFlowRate = (dispensedVolumeML / ((float)duration / 1000.0));
        Serial.print("Average Flow Rate: "); Serial.print(avgFlowRate, 2); Serial.println(" mL/s");
      }
      Serial.print("Duration: "); Serial.print(duration); Serial.println(" ms");
      Serial.println("--------------------------");
      Serial.println("Enter command (e.g., V100-F2.2):");
    }
  } // end if(dispensingActive)
} // end loop