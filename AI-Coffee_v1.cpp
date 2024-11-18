/*
  Coffee Machine Control v1
  Author: Naomi Gonzalez 
  Date: Nov 2024

  Description:
  This sketch allows you to control first prototype of AI Coffee.
  It controls a motor to brew the coffee inside the centrifugal drum using a Readytosky 40A ESC.
  It controls water amount to brew coffee using a KEURIG K25 Water Pump 12V CJWP27-AC12C6B with L298N.
  Commands are input via the Serial Monitor in the pattern "R-100 D-5 V-25 R-0 D-10".
  It manages motor speed, pump volume, delays, and queues up to 3 pump commands.
  It also logs relevant data to a Supabase database.

  Connections:
  - Motor Control (Readytosky 40A ESC)
    - Port C = Blue motor wire
    - Port B = Red motor wire
    - Port A = Black motor wire
    - Black Wire (-) = Ground 
    - Red Wire (+) = Power supply voltage (24V)
    - White skinny = GPIO PIN 18 ESP32-S3
    - Black skinny = GND ESP32-S3

  - Water Pump Control (KEURIG K25 Water Pump 12V CJWP27-AC12C6B with L298N)
    - OUT1 = Red wire water pump V+
    - OUT2 = Black wire water pump GND
    - +12V = Power supply voltage (12V)
    - GND = Power supply GND; ESP32-S3 GND
    - IN1 = GPIO PIN 16
    - IN2 = GPIO PIN 17
*/

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ------------------- Pin Definitions and Constants ----------------------
#define PWM_FREQ        500         // PWM Hz frequency for motor control
#define PWM_RESOLUTION  8           // 8-bit resolution (0-255)
#define PWM_CHANNEL     0           // LEDC channel (0-15)
#define PWM_PIN         18          // GPIO PIN for motor PWM

#define PUMP_IN1_PIN    16          // GPIO PIN 16 for pump control (IN1)
#define PUMP_IN2_PIN    17          // GPIO PIN 17 for pump control (IN2)

#define COMMAND_QUEUE_SIZE 20

// -------------------- WiFi and Supabase Configuration -------------------
/*
#define WIFI_SSID       "fill_here"             
#define WIFI_PASSWORD   "fill_here"                 

#define SUPABASE_URL    "fill_here"
#define SUPABASE_KEY    "fill_here" 
*/

// ------------------------------------------------------------------------
enum CommandType {
  CMD_R,   // Set motor RPM
  CMD_D,   // Delay
  CMD_V    // Pump volume
};

struct Command {
  CommandType type;
  int value;
};

// Command Queue
Command commandQueue[COMMAND_QUEUE_SIZE];
int commandQueueFront = 0;
int commandQueueRear = 0;
int commandQueueCount = 0;

// Pump State
bool isPumping = false;
unsigned long pumpEndTime = 0;
unsigned long pumpVolume = 0;

// Delay State
bool isDelaying = false;
unsigned long delayEndTime = 0;

// Motor State
int currentSpeed = 0;

void enqueueCommand(Command cmd);
bool dequeueCommand(Command &cmd);
void parseInputString(String input);
void handleCommand(Command cmd);
void setMotorSpeed(int speedPercentage);
void startPump(unsigned long volume_ml);
//void uploadData(int rpm, double duration_s, unsigned long volume_pumped, double actual_pump_time_s);

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }

  // Motor setup
  ledcSetup(PWM_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(PWM_PIN, PWM_CHANNEL);
  ledcWrite(PWM_CHANNEL, 191); // Motor off

  // Pump setup
  pinMode(PUMP_IN1_PIN, OUTPUT);
  pinMode(PUMP_IN2_PIN, OUTPUT);
  digitalWrite(PUMP_IN1_PIN, LOW);
  digitalWrite(PUMP_IN2_PIN, LOW); // Pump off

  /*
  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
  */ 
  
  // Welcome Message
  Serial.println("-------------------------------------------------");
  Serial.println("Team 3: AI Coffee v1.0.0");
  Serial.println("Enter commands in the pattern: R-100 D-5 V-25 R-0 D-10");
  Serial.println("-------------------------------------------------");
}

void loop(){
  // Check for serial input
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() > 0) {
      parseInputString(input);
    }
  }

  // Execute commands if not in DELAY state
  if (!isDelaying && commandQueueCount > 0) {
    Command nextCmd;
    if (dequeueCommand(nextCmd)) {
      handleCommand(nextCmd);
    }
  }

  // Handle Pumping
  if (isPumping && millis() >= pumpEndTime) {
    // Stop Pump
    digitalWrite(PUMP_IN1_PIN, LOW);
    digitalWrite(PUMP_IN2_PIN, LOW);
    unsigned long actualPumpTime = (pumpEndTime - (pumpVolume * 3000UL / 25UL)) - (pumpEndTime - millis());
    Serial.println("Pump OFF.");

    //uploadData(currentSpeed, 0, pumpVolume, actualPumpTime / 1000.0);

    isPumping = false;
  }

  // Handle Delay
  if (isDelaying && millis() >= delayEndTime) {
    Serial.println("Delay completed.");
    isDelaying = false;
  }

  delay(10);
}

// --------------------------- Command Queue Functions ---------------------------

void enqueueCommand(Command cmd) {
  if (commandQueueCount < COMMAND_QUEUE_SIZE) {
    commandQueue[commandQueueRear] = cmd;
    commandQueueRear = (commandQueueRear + 1) % COMMAND_QUEUE_SIZE;
    commandQueueCount++;
  } else {
    Serial.println("Command queue full. Command ignored.");
  }
}

bool dequeueCommand(Command &cmd) {
  if (commandQueueCount > 0) {
    cmd = commandQueue[commandQueueFront];
    commandQueueFront = (commandQueueFront + 1) % COMMAND_QUEUE_SIZE;
    commandQueueCount--;
    return true;
  }
  return false;
}

// --------------------------- Input Parsing Function ---------------------------

void parseInputString(String input) {
  Serial.print("Received Input: ");
  Serial.println(input);

  // Split the input string by spaces
  int startIdx = 0;
  int spaceIdx = input.indexOf(' ');

  while (spaceIdx != -1) {
    String token = input.substring(startIdx, spaceIdx);
    startIdx = spaceIdx + 1;
    spaceIdx = input.indexOf(' ', startIdx);

    if (token.length() > 2 && token.charAt(1) == '-') {
      char cmdType = token.charAt(0);
      String valueStr = token.substring(2);
      int value = valueStr.toInt();
      Command cmd;

      switch (cmdType) {
        case 'R':
          cmd.type = CMD_R;
          cmd.value = value;
          enqueueCommand(cmd);
          break;
        case 'D':
          cmd.type = CMD_D;
          cmd.value = value;
          enqueueCommand(cmd);
          break;
        case 'V':
          cmd.type = CMD_V;
          cmd.value = value;
          enqueueCommand(cmd);
          break;
        default:
          Serial.print("Unknown command type: ");
          Serial.println(cmdType);
          break;
      }
    } else {
      Serial.print("Invalid command format: ");
      Serial.println(token);
    }
  }

  // Handle the last token
  String lastToken = input.substring(startIdx);
  if (lastToken.length() > 2 && lastToken.charAt(1) == '-') {
    char cmdType = lastToken.charAt(0);
    String valueStr = lastToken.substring(2);
    int value = valueStr.toInt();
    Command cmd;

    switch (cmdType) {
      case 'R':
        cmd.type = CMD_R;
        cmd.value = value;
        enqueueCommand(cmd);
        break;
      case 'D':
        cmd.type = CMD_D;
        cmd.value = value;
        enqueueCommand(cmd);
        break;
      case 'V':
        cmd.type = CMD_V;
        cmd.value = value;
        enqueueCommand(cmd);
        break;
      default:
        Serial.print("Unknown command type: ");
        Serial.println(cmdType);
        break;
    }
  } else if (lastToken.length() > 0) {
    Serial.print("Invalid command format: ");
    Serial.println(lastToken);
  }

  Serial.println("Commands enqueued.");
}

// --------------------------- Command Handler Function ---------------------------

void handleCommand(Command cmd) {
  switch (cmd.type) {
    case CMD_R:
      setMotorSpeed(cmd.value);
      break;
    case CMD_D:
      isDelaying = true;
      delayEndTime = millis() + cmd.value * 1000UL;
      Serial.print("Delaying for ");
      Serial.print(cmd.value);
      Serial.println(" seconds.");
      break;
    case CMD_V:
      if (!isPumping) {
        startPump(cmd.value);
      } else {
        Serial.println("Skipped command because pump is still running.");
        // Do not send data to DB
      }
      break;
    default:
      Serial.println("Unhandled command type.");
      break;
  }
}

// --------------------------- Motor Control Function ---------------------------

void setMotorSpeed(int speedPercentage) {
  speedPercentage = constrain(speedPercentage, 0, 100);

  // Map speed percentage to PWM duty cycle
  int pwmDuty = map(speedPercentage, 0, 100, 191, 253);

  ledcWrite(PWM_CHANNEL, pwmDuty);
  currentSpeed = speedPercentage;

  Serial.print("Motor speed set to ");
  Serial.print(speedPercentage);
  Serial.println("%");

  //uploadData(currentSpeed, 0, 0, 0); // change?
}

// --------------------------- Pump Control Function ---------------------------

void startPump(unsigned long volume_ml) {
  // Calculate pump duration based on 25ml per 3 seconds
  unsigned long duration_ms = (volume_ml * 3000UL) / 25UL;

  // Start Pump
  digitalWrite(PUMP_IN1_PIN, HIGH);
  digitalWrite(PUMP_IN2_PIN, LOW);
  pumpEndTime = millis() + duration_ms;
  pumpVolume = volume_ml;
  isPumping = true;

  Serial.print("Pump ON to pump ");
  Serial.print(volume_ml);
  Serial.println(" ml.");

  //uploadData(currentSpeed, 0, pumpVolume, duration_ms / 1000.0); // change?
}

// --------------------------- Data Upload Function ---------------------------

/*
void uploadData(int rpm, double duration_s, unsigned long volume_pumped, double actual_pump_time_s) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SUPABASE_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("apikey", SUPABASE_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_KEY);

    // Prepare JSON payload
    StaticJsonDocument<256> json;
    json["rpm"] = rpm;
    json["duration_s"] = duration_s;
    json["volume_pumped_ml"] = volume_pumped;
    json["actual_pump_time_s"] = actual_pump_time_s;

    String requestBody;
    serializeJson(json, requestBody);

    // Send POST request
    int httpResponseCode = http.POST(requestBody);

    if (httpResponseCode > 0) {
      Serial.print("Data uploaded successfully. HTTP Response code: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Error uploading data. HTTP Response code: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("WiFi not connected. Unable to upload data.");
  }
}
*/
