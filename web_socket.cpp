/*
  Coffee Machine Control v1 with HTTP Interface
  Modified from original by Naomi and Krish
  Date: March 2025

  Description:
  This sketch allows you to control the first prototype of AI Coffee via HTTP.
  It manages motor speed, pump volume, delays, and logs relevant data to a Supabase database.
  Commands are input via HTTP requests in the pattern "R-100 D-5 V-25 R-0 D-10".

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


  USAGE INSTRUCTIONS:
  ------------------
  This code allows you to control the AI Coffee machine using HTTP requests instead of
  just serial commands. Once uploaded to the ESP32:

  1. CONNECTING:
     - The ESP32 will connect to WiFi (using credentials defined in WIFI_SSID and WIFI_PASSWORD)
     - It will display its IP address in the Serial Monitor
     - It will also attempt to set up mDNS at "aicoffee.local" for easier access

  2. SENDING COMMANDS:
     Method A - Web Interface:
     - Open a browser and navigate to http://[ESP_IP_ADDRESS]/ or http://aicoffee.local/
     - Use the form to enter commands like "R-100 D-5 V-25 R-0 D-10"
     - Command responses will appear on the page

     Method B - HTTP Requests:
     - Send POST requests to http://[ESP_IP_ADDRESS]/command with parameter "cmd"
     - Example: curl -X POST http://[ESP_IP_ADDRESS]/command -d "cmd=R-100 D-5 V-25"
     - Response will contain command output and status messages

  3. CHECKING STATUS:
     - Send GET request to http://[ESP_IP_ADDRESS]/status
     - Returns JSON with current motor speed, pump status, delay status, etc.

  4. COMMAND FORMAT:
     - R-xxx: Set motor speed (0-100%)
     - D-xxx: Delay for xxx seconds
     - V-xxx: Pump xxx ml of water
     - Commands can be chained with spaces: "R-100 D-5 V-25 R-0 D-10"

  WHAT TO EXPECT:
  --------------
  - The ESP32 will set up an HTTP server on port 80
  - Commands via HTTP will be processed in the same way as serial commands
  - Command execution status will be returned in the HTTP response
  - The web interface provides a simple way to control the machine without special tools
  - Status information is continuously available via the /status endpoint
  - Data will still be logged to Supabase as in the original version
  - Serial monitor also shows debug information
*/

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <WebServer.h>
#include <ESPmDNS.h>

// ------------------- Pin Definitions and Constants ----------------------
#define PWM_FREQ        500         // PWM frequency for motor control
#define PWM_RESOLUTION  8           // 8-bit resolution (0-255)
#define PWM_CHANNEL     0           // LEDC channel (0-15)
#define PWM_PIN         18          // GPIO PIN for motor PWM

#define PUMP_IN1_PIN    16          // GPIO PIN 16 for pump control (IN1)
#define PUMP_IN2_PIN    17          // GPIO PIN 17 for pump control (IN2)

#define COMMAND_QUEUE_SIZE 20       // Size of the command queue
#define WEB_SERVER_PORT    80       // HTTP server port

// -------------------- WiFi and Supabase Configuration -------------------
#define WIFI_SSID       "Krish"              // Your WiFi SSID
#define WIFI_PASSWORD   "krish999"          // Your WiFi password

#define SUPABASE_URL    "https://oalhkndyagbfonwjnqya.supabase.co/rest/v1/control_parameters"  // Supabase endpoint
#define SUPABASE_KEY    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9hbGhrbmR5YWdiZm9ud2pucXlhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzEwMTM4OTIsImV4cCI6MjA0NjU4OTg5Mn0.lxSq85mwUwJMlbRlJfX6Z9HoY5r01E2kxW9DYFLvrCQ"       // Supabase API key

#define ESP_USERNAME "admin"
#define ESP_PASSWORD "brewsecure123"

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
int currentInputIndex = 1;        // Tracks which input_X and time_X to use

// Response buffer for HTTP responses
String responseBuffer = "";
bool responseReady = false;

// Web Server
WebServer server(WEB_SERVER_PORT);

// ---------------------- Function Prototypes -----------------------------
void enqueueCommand(Command cmd);
bool dequeueCommand(Command &cmd);
void parseInputString(String input);
void handleCommand(Command cmd);
void setMotorSpeed(int speedPercentage);
void startPump(unsigned long volume_ml);
void uploadData(int coffeeRunId, const char* input_json, const char* time_json, int inputIndex);

// HTTP Server handlers
void handleRoot();
void handleCommand();
void handleNotFound();
void handleStatus();

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
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // Set up mDNS responder
  if (MDNS.begin("aicoffee")) {
    Serial.println("mDNS responder started - you can access at http://aicoffee.local");
  }

  // Set up the web server routes
  server.on("/", HTTP_GET, handleRoot);
  server.on("/command", HTTP_POST, handleCommand);
  server.on("/status", HTTP_GET, handleStatus);
  server.onNotFound(handleNotFound);
  
  // Start the web server
  server.begin();
  Serial.println("HTTP server started");

  // Welcome Message
  Serial.println("-------------------------------------------------");
  Serial.println("AI Coffee Machine v1.1.0 - HTTP Enabled");
  Serial.println("Send commands via HTTP POST to /command");
  Serial.println("Example: curl -X POST http://ESP_IP_ADDRESS/command -d \"cmd=R-100 D-5 V-25 R-0 D-10\"");
  Serial.println("-------------------------------------------------");
}

// -------------------------- Arduino Loop --------------------------------
void loop() {
  // Handle HTTP requests
  server.handleClient();

  // Check for serial input (keeping this for debugging)
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() > 0) {
      responseBuffer = ""; // Clear response buffer
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
    String message = "Pump OFF.";
    Serial.println(message);
    responseBuffer += message + "\n";
    isPumping = false;
  }

  // End delay if the scheduled time has passed
  if (isDelaying && millis() >= delayEndTime) {
    String message = "Delay completed.";
    Serial.println(message);
    responseBuffer += message + "\n";
    isDelaying = false;
    
    // If we've completed all commands and delays, mark response as ready
    if (commandQueueCount == 0) {
      responseReady = true;
    }
  }

  delay(10); // Small delay to stabilize loop
}

// ------------------------ HTTP Server Handlers --------------------------
void handleRoot() {
  String html = "<html><head><title>AI Coffee Machine Control</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body { font-family: Arial, sans-serif; margin: 20px; }";
  html += "h1 { color: #333366; }";
  html += "form { margin: 20px 0; }";
  html += "input, button { padding: 8px; margin: 5px 0; }";
  html += "input[type='text'] { width: 80%; }";
  html += "button { background-color: #4CAF50; color: white; border: none; cursor: pointer; }";
  html += "pre { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }";
  html += "</style></head><body>";
  html += "<h1>AI Coffee Machine Control</h1>";
  html += "<p>Enter commands in the pattern: R-100 D-5 V-25 R-0 D-10</p>";
  html += "<form id='cmdForm'>";
  html += "<input type='text' id='cmdInput' placeholder='Enter commands (e.g., R-100 D-5 V-25)'>";
  html += "<button type='button' onclick='sendCommand()'>Send Command</button>";
  html += "</form>";
  html += "<h2>Response:</h2>";
  html += "<pre id='response'></pre>";
  html += "<h2>Machine Status:</h2>";
  html += "<pre id='status'>Loading...</pre>";
  
  html += "<script>";
  html += "function sendCommand() {";
  html += "  const cmd = document.getElementById('cmdInput').value;";
  html += "  if (!cmd) return;";
  html += "  fetch('/command', {";
  html += "    method: 'POST',";
  html += "    headers: {'Content-Type': 'application/x-www-form-urlencoded'},";
  html += "    body: 'cmd=' + encodeURIComponent(cmd)";
  html += "  })";
  html += "  .then(response => response.text())";
  html += "  .then(data => {";
  html += "    document.getElementById('response').textContent = data;";
  html += "    updateStatus();";
  html += "  });";
  html += "}";
  
  html += "function updateStatus() {";
  html += "  fetch('/status')";
  html += "  .then(response => response.json())";
  html += "  .then(data => {";
  html += "    document.getElementById('status').textContent = JSON.stringify(data, null, 2);";
  html += "  });";
  html += "}";
  
  html += "// Update status every 2 seconds";
  html += "setInterval(updateStatus, 2000);";
  html += "updateStatus();";
  html += "</script>";
  
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

void handleCommand() {
  if (!server.hasArg("cmd")) {
    server.send(400, "text/plain", "Bad Request: Missing 'cmd' parameter");
    return;
  }
  
  String cmd = server.arg("cmd");
  if (cmd.length() == 0) {
    server.send(400, "text/plain", "Bad Request: Empty command");
    return;
  }
  
  // Clear previous response buffer and parse the input
  responseBuffer = "";
  responseReady = false;
  parseInputString(cmd);
  
  // Wait for commands to complete (with timeout)
  unsigned long startTime = millis();
  const unsigned long maxWaitTime = 30000; // 30 seconds max wait
  
  while (!responseReady && 
         (isDelaying || isPumping || commandQueueCount > 0) && 
         (millis() - startTime < maxWaitTime)) {
    // Process commands while waiting
    server.handleClient();
    
    // If not delaying, execute next command
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
      String message = "Pump OFF.";
      Serial.println(message);
      responseBuffer += message + "\n";
      isPumping = false;
    }
    
    // End delay if the scheduled time has passed
    if (isDelaying && millis() >= delayEndTime) {
      String message = "Delay completed.";
      Serial.println(message);
      responseBuffer += message + "\n";
      isDelaying = false;
    }
    
    delay(10);
  }
  
  // If timed out or all commands processed, send response
  if (responseBuffer.length() == 0) {
    responseBuffer = "Commands enqueued, but no immediate output.";
  }
  
  server.send(200, "text/plain", responseBuffer);
}

void handleStatus() {
  StaticJsonDocument<256> statusJson;
  
  statusJson["motor_speed"] = currentSpeed;
  statusJson["is_pumping"] = isPumping;
  statusJson["is_delaying"] = isDelaying;
  statusJson["commands_queued"] = commandQueueCount;
  
  if (isPumping) {
    statusJson["pump_volume_ml"] = pumpVolume;
    statusJson["pump_time_remaining_ms"] = (pumpEndTime > millis()) ? (pumpEndTime - millis()) : 0;
  }
  
  if (isDelaying) {
    statusJson["delay_time_remaining_ms"] = (delayEndTime > millis()) ? (delayEndTime - millis()) : 0;
  }
  
  String response;
  serializeJson(statusJson, response);
  server.send(200, "application/json", response);
}

void handleNotFound() {
  server.send(404, "text/plain", "404: Not Found");
}

// ------------------------ Command Queue Functions -----------------------
void enqueueCommand(Command cmd) {
  if (commandQueueCount < COMMAND_QUEUE_SIZE) {
    commandQueue[commandQueueRear] = cmd;
    commandQueueRear = (commandQueueRear + 1) % COMMAND_QUEUE_SIZE;
    commandQueueCount++;
  } else {
    String message = "Command queue full. Command ignored.";
    Serial.println(message);
    responseBuffer += message + "\n";
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
  String message = "Received Input: " + input;
  Serial.println(message);
  responseBuffer += message + "\n";

  // Validate command format
  if (input.indexOf('R-') == -1 && 
      input.indexOf('D-') == -1 && 
      input.indexOf('V-') == -1) {
    message = "Error: Invalid command format. Must contain R-/D-/V- commands";
    Serial.println(message);
    responseBuffer += message + "\n";
    return;
  }

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

  message = "Commands enqueued.";
  Serial.println(message);
  responseBuffer += message + "\n";
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
        String message = "Unknown command type: " + String(cmdType);
        Serial.println(message);
        responseBuffer += message + "\n";
        break;
    }
  } else {
    String message = "Invalid command format: " + token;
    Serial.println(message);
    responseBuffer += message + "\n";
  }
}

// ------------------------- Command Handlers -----------------------------
void handleCommand() {
  // Basic Authentication Check
  if (!server.authenticate(ESP_USERNAME, ESP_PASSWORD)) {
    server.requestAuthentication();
    return;
  }

  if (!server.hasArg("cmd")) {
    server.send(400, "text/plain", "Bad Request: Missing 'cmd' parameter");
    return;
  }
  
  String cmd = server.arg("cmd");
  if (cmd.length() == 0) {
    server.send(400, "text/plain", "Bad Request: Empty command");
    return;
  }
  
  // Clear previous response buffer and parse the input
  responseBuffer = "";
  responseReady = false;
  parseInputString(cmd);
  
  // Wait for commands to complete (with timeout)
  unsigned long startTime = millis();
  const unsigned long maxWaitTime = 30000; // 30 seconds max wait
  
  while (!responseReady && 
         (isDelaying || isPumping || commandQueueCount > 0) && 
         (millis() - startTime < maxWaitTime)) {
    // Process commands while waiting
    server.handleClient();
    
    // If not delaying, execute next command
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
      String message = "Pump OFF.";
      Serial.println(message);
      responseBuffer += message + "\n";
      isPumping = false;
    }
    
    // End delay if the scheduled time has passed
    if (isDelaying && millis() >= delayEndTime) {
      String message = "Delay completed.";
      Serial.println(message);
      responseBuffer += message + "\n";
      isDelaying = false;
    }
    
    delay(10);
  }
  
  // If timed out or all commands processed, send response
  if (responseBuffer.length() == 0) {
    responseBuffer = "Commands enqueued, but no immediate output.";
  }
  
  server.send(200, "text/plain", responseBuffer);
}

void setMotorSpeed(int speedPercentage) {
  speedPercentage = constrain(speedPercentage, 0, 100);
  int pwmDuty = map(speedPercentage, 0, 100, 191, 253);
  ledcWrite(PWM_CHANNEL, pwmDuty);
  currentSpeed = speedPercentage;

  String message = "Motor speed set to " + String(speedPercentage) + "%";
  Serial.println(message);
  responseBuffer += message + "\n";

  // Upload data for motor control
  char input_json[128];
  snprintf(input_json, sizeof(input_json), R"({"letter": "R", "value": %d})", speedPercentage);
  uploadData(1, input_json, "{}", currentInputIndex++);
}

void startPump(unsigned long volume_ml) {
  unsigned long duration_ms = (volume_ml * 3000UL) / 25UL;
  digitalWrite(PUMP_IN1_PIN, HIGH);
  digitalWrite(PUMP_IN2_PIN, LOW);
  pumpEndTime = millis() + duration_ms;
  pumpVolume = volume_ml;
  isPumping = true;

  String message = "Pump ON to pump " + String(volume_ml) + " ml.";
  Serial.println(message);
  responseBuffer += message + "\n";

  // Upload data for pump control
  char input_json[128], time_json[128];
  snprintf(input_json, sizeof(input_json), R"({"letter": "V", "value": %lu})", volume_ml);
  snprintf(time_json, sizeof(time_json), R"({"delay": 0, "duration": %.2f})", duration_ms / 1000.0);
  uploadData(1, input_json, time_json, currentInputIndex++);
}

// ---------------------- Supabase Data Upload ----------------------------
void uploadData(int coffeeRunId, const char* input_json, const char* time_json, int inputIndex) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SUPABASE_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("apikey", SUPABASE_KEY);

    StaticJsonDocument<512> json;
    json["coffee_run_id"] = coffeeRunId;
    json[String("input_") + inputIndex] = input_json;
    json[String("time_") + inputIndex] = time_json;

    String requestBody;
    serializeJson(json, requestBody);

    int httpResponseCode = http.POST(requestBody);
    if (httpResponseCode > 0) {
      String message = "Data uploaded successfully. HTTP Response code: " + String(httpResponseCode);
      Serial.println(message);
      // Not adding to responseBuffer to keep it cleaner for users
    } else {
      String message = "Error uploading data. HTTP Response code: " + String(httpResponseCode);
      Serial.println(message);
      // Not adding to responseBuffer to keep it cleaner for users
    }

    http.end();
  } else {
    String message = "WiFi not connected. Unable to upload data.";
    Serial.println(message);
    // Not adding to responseBuffer to keep it cleaner for users
  }
}