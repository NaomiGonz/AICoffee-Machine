/*
  Coffee Machine Control v1
  Author: Naomi Gonzalez 
  Date: Nov 2024

  Description:
  This sketch allows you to control the first prototype of AI Coffee.
  It manages motor speed, pump volume, delays, and logs relevant data to a Supabase database in structured JSON format.

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
#define PWM_FREQ        500         // PWM frequency for motor control
#define PWM_RESOLUTION  8           // 8-bit resolution (0-255)
#define PWM_CHANNEL     0           // LEDC channel (0-15)
#define PWM_PIN         18          // GPIO PIN for motor PWM

#define PUMP_IN1_PIN    16          // GPIO PIN 16 for pump control (IN1)
#define PUMP_IN2_PIN    17          // GPIO PIN 17 for pump control (IN2)

#define COMMAND_QUEUE_SIZE 20       // Size of the command queue

// -------------------- WiFi and Supabase Configuration -------------------
#define WIFI_SSID       "your_wifi_ssid"             // Your WiFi SSID
#define WIFI_PASSWORD   "your_wifi_password"         // Your WiFi password

#define SUPABASE_URL    "https://oalhkndyagbfonwjnqya.supabase.co/rest/v1/control_parameters"  // Supabase endpoint
#define SUPABASE_KEY    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9hbGhrbmR5YWdiZm9ud2pucXlhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzEwMTM4OTIsImV4cCI6MjA0NjU4OTg5Mn0.lxSq85mwUwJMlbRlJfX6Z9HoY5r01E2kxW9DYFLvrCQ"         // Supabase API key

// ------------------------- Command Types and State ----------------------
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

// State Variables
bool isPumping = false;           // Pump state
unsigned long pumpEndTime = 0;    // End time for pumping
unsigned long pumpVolume = 0;     // Volume to pump

bool isDelaying = false;          // Delay state
unsigned long delayEndTime = 0;   // End time for delay

int currentSpeed = 0;             // Current motor speed percentage

// ---------------------- Function Prototypes -----------------------------
void enqueueCommand(Command cmd);
bool dequeueCommand(Command &cmd);
void parseInputString(String input);
void handleCommand(Command cmd);
void setMotorSpeed(int speedPercentage);
void startPump(unsigned long volume_ml);
void uploadData(int coffeeRunId, const char* input_json, const char* time_json);

// ------------------------- Arduino Setup --------------------------------
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

  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");

  // Welcome Message
  Serial.println("-------------------------------------------------");
  Serial.println("AI Coffee Machine v1.0.0");
  Serial.println("Enter commands in the pattern: R-100 D-5 V-25 R-0 D-10");
  Serial.println("-------------------------------------------------");
}

// -------------------------- Arduino Loop --------------------------------
void loop() {
  // Check for serial input
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() > 0) {
      parseInputString(input);
    }
  }

  // Execute next command if not delaying
  if (!isDelaying && commandQueueCount > 0) {
    Command nextCmd;
    if (dequeueCommand(nextCmd)) {
      handleCommand(nextCmd);
    }
  }

  // Stop pump after the scheduled duration
  if (isPumping && millis() >= pumpEndTime) {
    digitalWrite(PUMP_IN1_PIN, LOW);
    digitalWrite(PUMP_IN2_PIN, LOW);
    Serial.println("Pump OFF.");
    isPumping = false;
  }

  // End delay if the scheduled time has passed
  if (isDelaying && millis() >= delayEndTime) {
    Serial.println("Delay completed.");
    isDelaying = false;
  }

  delay(10); // Small delay to stabilize loop
}

// ------------------------ Command Queue Functions -----------------------
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

// ------------------------ Input Parsing Functions -----------------------
void parseInputString(String input) {
  Serial.print("Received Input: ");
  Serial.println(input);

  int startIdx = 0;
  int spaceIdx = input.indexOf(' ');

  while (spaceIdx != -1) {
    String token = input.substring(startIdx, spaceIdx);
    startIdx = spaceIdx + 1;
    spaceIdx = input.indexOf(' ', startIdx);
    processToken(token);
  }

  // Process the last token
  String lastToken = input.substring(startIdx);
  processToken(lastToken);

  Serial.println("Commands enqueued.");
}

void processToken(String token) {
  if (token.length() > 2 && token.charAt(1) == '-') {
    char cmdType = token.charAt(0);
    int value = token.substring(2).toInt();
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

// ------------------------- Command Handlers -----------------------------
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
      startPump(cmd.value);
      break;
    default:
      Serial.println("Unhandled command type.");
      break;
  }
}

void setMotorSpeed(int speedPercentage) {
  speedPercentage = constrain(speedPercentage, 0, 100);
  int pwmDuty = map(speedPercentage, 0, 100, 191, 253);
  ledcWrite(PWM_CHANNEL, pwmDuty);
  currentSpeed = speedPercentage;

  Serial.print("Motor speed set to ");
  Serial.print(speedPercentage);
  Serial.println("%");

  // Upload data for motor control
  char input_json[128];
  snprintf(input_json, sizeof(input_json), R"({"letter": "R", "value": %d})", speedPercentage);
  uploadData(1, input_json, "{}");
}

void startPump(unsigned long volume_ml) {
  unsigned long duration_ms = (volume_ml * 3000UL) / 25UL;
  digitalWrite(PUMP_IN1_PIN, HIGH);
  digitalWrite(PUMP_IN2_PIN, LOW);
  pumpEndTime = millis() + duration_ms;
  pumpVolume = volume_ml;
  isPumping = true;

  Serial.print("Pump ON to pump ");
  Serial.print(volume_ml);
  Serial.println(" ml.");

  // Upload data for pump control
  char input_json[128], time_json[128];
  snprintf(input_json, sizeof(input_json), R"({"letter": "V", "value": %lu})", volume_ml);
  snprintf(time_json, sizeof(time_json), R"({"delay": 0, "duration": %.2f})", duration_ms / 1000.0);
  uploadData(1, input_json, time_json);
}

// ---------------------- Supabase Data Upload ----------------------------
void uploadData(int coffeeRunId, const char* input_json, const char* time_json) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SUPABASE_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("apikey", SUPABASE_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_KEY);

    StaticJsonDocument<512> json;
    json["coffee_run_id"] = coffeeRunId; // Autogenerated coffee run ID
    json["input"] = input_json;         // Input JSON
    json["time"] = time_json;           // Time JSON

    String requestBody;
    serializeJson(json, requestBody);

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
