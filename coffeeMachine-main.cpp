/*
  Coffee Machine Control v2

  Author: Naomi 
  Date: March 2025
  Note: Inspiration and parts taken from the original Coffee Machine Control code inside test_code/ folder.

  Description: This code controls a coffee machine with the following components:
    - Barrel Motor
    - Grinder Motor
    - Heater
    - Pump
  
  The coffee machine can be controlled via a web interface or serial commands.
  The following commands examples are supported:
    - R-100: Set barrel motor speed to 100%
    - G-50: Set grinder motor speed to 50%
    - D-5: Delay for 5 seconds
    - V-25: Run pump for 25 seconds
    - H-75: Turn heater on at 75% power
  
  The code also includes safety features:
    - Heater auto-off after 5 seconds of pump inactivity
    - Heater cooldown after pump stops
    - Pump cooldown after heater stops


  HOW TO USE:
  - Uncomment one of the operation modes: WEB_MODE or SERIAL_MODE
  - Upload the code to the ESP32
  Web Mode Usage
    Setup:
      1. Connect to the WiFi network by updating variables ssid and password
      2. Open a web browser and navigate to "http://aicoffee.local"
    Command Interface:
      - Send commands via POST
        curl -X POST http://aicoffee.local/command -d "cmd=R-100 D-5 V-25"
      - Check status via GET
        curl http://aicoffee.local/status
    Expected Correct Behavior:
      - Immediate 200 OK response for valid commands
      - 503 Service Unavailable for full queue
      - 400 Bad Request for invalid commands
      - Status shows device states and queue usage
  Serial Mode Usage
    Setup:
      1. Connect to the ESP32 via serial monitor (115200 baud)
    Command Interface:
      - Send commands via serial monitor (press <ENTER> after each command)
        R-100 G-50 D-5 V-25 H-75
    Expected Correct Behavior:
      - Immediate processing of commands
      - No response or status available
*/


#include <Arduino.h>

// Operation Mode - Uncomment ONE
#define WEB_MODE
// #define SERIAL_MODE

#ifdef WEB_MODE
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#endif

// Pin Definitions
#define BARREL_MOTOR_PIN 18
#define GRINDER_MOTOR_PIN 19
#define HEATER_PIN 23
#define PUMP_IN1_PIN 16
#define PUMP_IN2_PIN 17

// PWM Configuration
#define PWM_FREQ 5000
#define PWM_RES 8
enum PWMChannels {
  BARREL_CHANNEL = 0,
  GRINDER_CHANNEL = 1,
  HEATER_CHANNEL = 2
};

// Safety Parameters
#define HEATER_TIMEOUT 5000    // 5 seconds
#define POST_PUMP_COOLDOWN 1000
#define QUEUE_SIZE 20          // Command queue capacity

#ifdef WEB_MODE
// WiFi Configuration
const char* ssid = "Krish";
const char* password = "krish999";
WebServer server(80);
#endif

// Command Processing
enum CommandType { CMD_R, CMD_G, CMD_D, CMD_V, CMD_H };
struct Command { CommandType type; int value; };
Command cmdQueue[QUEUE_SIZE];
int queueFront = 0, queueRear = 0, queueCount = 0;

// Device States
bool barrelRunning = false;
bool grinderRunning = false;
bool heaterActive = false;
bool pumpRunning = false;
unsigned long heaterStartTime = 0;
bool pumpUsedSinceHeaterOn = false;
unsigned long pumpStopTime = 0;
unsigned long delayEndTime = 0;

#ifdef WEB_MODE
// ================= WEB SERVER HANDLERS =================
void handleRoot() {
  String html = R"(
  <html><head><title>Coffee Machine Control</title>
  <style>body {font-family: Arial; margin: 20px;}
  form {margin: 20px 0;} input, button {padding: 8px;}
  .status {border: 1px solid #ccc; padding: 10px; margin-top: 20px;}
  </style></head><body>
  <h1>Coffee Machine Control</h1>
  <form action="/command" method="POST">
  <input type="text" name="cmd" placeholder="R-100 D-5 V-25">
  <button type="submit">Send</button></form>
  <div class="status">
  <h3>Status</h3>
  <pre id="status">%STATUS%</pre>
  </div>
  <script>
  function updateStatus() {
    fetch('/status').then(r => r.text()).then(t => {
      document.getElementById('status').textContent = t;
    });
  }
  setInterval(updateStatus, 1000);
  </script>
  </body></html>
  )";
  
  server.send(200, "text/html", html);
}

int countCommands(const String& input) {
  int count = 0;
  int start = 0;
  int end = 0;
  bool inCommand = false;

  while (start < input.length()) {
    end = input.indexOf(' ', start);
    if (end == -1) end = input.length();
    
    // Check valid command format: X-123
    if (end - start >= 3 && 
        input[start+1] == '-' && 
        isDigit(input[start+2])) {
      count++;
    }
    
    start = end + 1;
  }
  return count;
}

void handleCommand() {
  if (!server.hasArg("cmd")) {
    server.send(400, "text/plain", "Missing command");
    return;
  }

  String input = server.arg("cmd");
  input.trim();
  
  if (input.length() == 0) {
    server.send(400, "text/plain", "Empty command");
    return;
  }

  const int commandCount = countCommands(input);
  if (commandCount == 0) {
    server.send(400, "text/plain", "No valid commands");
    return;
  }

  const int availableSlots = QUEUE_SIZE - queueCount;
  if (commandCount > availableSlots) {
    server.send(503, "text/plain", 
      "Queue full. Required: " + String(commandCount) + 
      "/Available: " + String(availableSlots));
    return;
  }

  // Atomic command addition
  int start = 0;
  int end = 0;
  while (start < input.length()) {
    end = input.indexOf(' ', start);
    if (end == -1) end = input.length();
    
    if (end > start) {
      String token = input.substring(start, end);
      processToken(token);
    }
    
    start = end + 1;
  }

  server.send(200, "text/plain", 
    String(commandCount) + " commands queued");
}

void handleStatus() {
  String status = "Barrel: " + String(barrelRunning ? "ON" : "OFF") + "\n" +
                  "Grinder: " + String(grinderRunning ? "ON" : "OFF") + "\n" +
                  "Heater: " + String(heaterActive ? "ON" : "OFF") + "\n" +
                  "Pump: " + String(pumpRunning ? "ON" : "OFF") + "\n" +
                  "Queue: " + String(queueCount) + "/" + String(QUEUE_SIZE);
  server.send(200, "text/plain", status);
}
#endif

// ================= HARDWARE CONTROL =================
void setupPins() {
  ledcSetup(BARREL_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(BARREL_MOTOR_PIN, BARREL_CHANNEL);
  
  ledcSetup(GRINDER_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(GRINDER_MOTOR_PIN, GRINDER_CHANNEL);
  
  ledcSetup(HEATER_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(HEATER_PIN, HEATER_CHANNEL);
  
  pinMode(PUMP_IN1_PIN, OUTPUT);
  pinMode(PUMP_IN2_PIN, OUTPUT);
  digitalWrite(PUMP_IN1_PIN, LOW);
  digitalWrite(PUMP_IN2_PIN, LOW);
}

void processToken(const String& token) {
  if (token.length() < 3 || token[1] != '-') return;

  char cmdType = token[0];
  int value = token.substring(2).toInt();
  Command cmd;

  switch (cmdType) {
    case 'R': cmd.type = CMD_R; break;
    case 'G': cmd.type = CMD_G; break;
    case 'D': cmd.type = CMD_D; break;
    case 'V': cmd.type = CMD_V; break;
    case 'H': cmd.type = CMD_H; break;
    default: return;
  }
  cmd.value = value;

  // Add to queue
  if (queueCount < QUEUE_SIZE) {
    cmdQueue[queueRear] = cmd;
    queueRear = (queueRear + 1) % QUEUE_SIZE;
    queueCount++;
  }
}

void processCommand(const Command& cmd) {
  switch (cmd.type) {
    case CMD_R:
      ledcWrite(BARREL_CHANNEL, map(cmd.value, 0, 100, 0, 255));
      barrelRunning = (cmd.value > 0);
      break;

    case CMD_G:
      ledcWrite(GRINDER_CHANNEL, map(cmd.value, 0, 100, 0, 255));
      grinderRunning = (cmd.value > 0);
      break;

    case CMD_D:
      delayEndTime = millis() + cmd.value * 1000;
      break;

    case CMD_V: {
      unsigned long duration = (cmd.value * 3000) / 25;
      digitalWrite(PUMP_IN1_PIN, HIGH);
      pumpRunning = true;
      pumpStopTime = millis() + duration;
      pumpUsedSinceHeaterOn = true;
      break;
    }

    case CMD_H:
      ledcWrite(HEATER_CHANNEL, map(cmd.value, 0, 100, 0, 255));
      heaterActive = (cmd.value > 0);
      if (heaterActive) {
        heaterStartTime = millis();
        pumpUsedSinceHeaterOn = false;
      }
      break;
  }
}

void checkSafety() {
  if (heaterActive && !pumpUsedSinceHeaterOn && 
     (millis() - heaterStartTime > HEATER_TIMEOUT)) {
    ledcWrite(HEATER_CHANNEL, 0);
    heaterActive = false;
  }
}

// ================= MAIN FUNCTIONS =================
void setup() {
  Serial.begin(115200);
  setupPins();

#ifdef WEB_MODE
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  
  if (MDNS.begin("aicoffee")) {
    Serial.println("mDNS responder started");
  }

  server.on("/", handleRoot);
  server.on("/command", HTTP_POST, handleCommand);
  server.on("/status", HTTP_GET, handleStatus);
  server.begin();
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
#endif
}

void loop() {
#ifdef WEB_MODE
  server.handleClient();
#endif

#ifdef SERIAL_MODE
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    int start = 0;
    int end = 0;
    while ((end = input.indexOf(' ', start)) != -1) {
      if (end == -1) end = input.length();
      processToken(input.substring(start, end));
      start = end + 1;
    }
  }
#endif

  // Process command queue
  while (queueCount > 0 && millis() >= delayEndTime) {
    Command cmd = cmdQueue[queueFront];
    queueFront = (queueFront + 1) % QUEUE_SIZE;
    queueCount--;
    processCommand(cmd);
  }

  // Pump timeout
  if (pumpRunning && millis() >= pumpStopTime) {
    digitalWrite(PUMP_IN1_PIN, LOW);
    pumpRunning = false;
    if (heaterActive) {
      delayEndTime = millis() + POST_PUMP_COOLDOWN;
    }
  }

  // Heater cooldown after pump
  if (!pumpRunning && heaterActive && millis() >= delayEndTime) {
    ledcWrite(HEATER_CHANNEL, 0);
    heaterActive = false;
  }

  checkSafety();
  delay(10);
}
