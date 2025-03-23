#define FLOW_SENSOR_PIN 2    // Flow sensor (yellow wire)
#define IN1_PIN 16           // L298N Motor IN1
#define IN2_PIN 17           // L298N Motor IN2

volatile uint32_t pulseCount = 0;
float flowRate = 0.0;
float totalLiters = 0.0;
unsigned long lastFlowTime = 0;
bool wasFlowing = false;

// Pump State
enum PumpState { IDLE, RUNNING };
PumpState currentState = IDLE;
unsigned long pumpStartTime = 0;
unsigned long pumpDuration = 0;

// Serial Input
String inputString = "";
bool stringComplete = false;

const float calibrationFactor = 7.5; // Hz per L/min

void IRAM_ATTR handlePulse() {
  pulseCount++;
}

void setup() {
  Serial.begin(115200);

  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), handlePulse, RISING);

  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, LOW);

  inputString.reserve(50);
  lastFlowTime = millis();

  Serial.println("-------------------------------------------------");
  Serial.println("ESP32 Water Pump + Flow Sensor");
  Serial.println("Enter pump run time (sec), then press Enter.");
  Serial.println("-------------------------------------------------");
}

void loop() {
  unsigned long currentTime = millis();
  unsigned long elapsedFlowTime = currentTime - lastFlowTime;

  switch (currentState) {
    case IDLE:
      if (stringComplete) {
        pumpDuration = parseInput(inputString);
        if (pumpDuration > 0) {
          digitalWrite(IN1_PIN, HIGH);
          digitalWrite(IN2_PIN, LOW);
          pumpStartTime = millis();
          lastFlowTime = millis();
          currentState = RUNNING;
          Serial.print("Pump ON for ");
          Serial.print(pumpDuration / 1000);
          Serial.println(" seconds.");
        } else {
          Serial.println("Invalid input. Try again.");
        }
        inputString = "";
        stringComplete = false;
      }
      break;

    case RUNNING:
      if (currentTime - pumpStartTime >= pumpDuration) {
        digitalWrite(IN1_PIN, LOW);
        digitalWrite(IN2_PIN, LOW);
        currentState = IDLE;
        Serial.println("Pump OFF.");
        Serial.println("-------------------------------------------------");
        Serial.println("Enter pump run time (sec), then press Enter.");
      }

      // Flow measurement every 1 second
      if (elapsedFlowTime >= 1000) {
        detachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN));

        float hertz = (float)pulseCount / (elapsedFlowTime / 1000.0);
        flowRate = hertz / calibrationFactor;
        float liters = (flowRate / 60.0) * (elapsedFlowTime / 1000.0);
        totalLiters += liters;

        if (pulseCount > 0) {
          Serial.print("Flow Rate: ");
          Serial.print(flowRate);
          Serial.print(" L/min\tTotal: ");
          Serial.print(totalLiters, 3);
          Serial.println(" L");
          wasFlowing = true;
        } else {
          if (wasFlowing) {
            Serial.println("Warning: No flow detected — tank may be empty!");
            wasFlowing = false;
          } else {
            Serial.println("No flow detected.");
          }
        }

        pulseCount = 0;
        lastFlowTime = currentTime;
        attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), handlePulse, RISING);
      }
      break;
  }
}

// Handle serial input
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

// Parse seconds to milliseconds
unsigned long parseInput(String input) {
  input.trim();
  if (input.length() == 0) return 0;
  unsigned long seconds = input.toInt();
  if (seconds == 0 && input != "0") return 0;
  return seconds * 1000;
}
