#include <WiFi.h>
#include <WebSocketsServer.h>

// WiFi Credentials
#define WIFI_SSID     "Krish"
#define WIFI_PASSWORD "krish999"

// Motor and Pump Pins
#define MOTOR_PWM_PIN 18
#define PUMP_IN1_PIN  16
#define PUMP_IN2_PIN  17

// WebSocket Server on port 81
WebSocketsServer webSocket(81);

// Track states
int currentMotorSpeed = 0;
bool isPumping = false;

void setup() {
  Serial.begin(115200);
  
  // Setup motor
  ledcSetup(0, 500, 8);
  ledcAttachPin(MOTOR_PWM_PIN, 0);
  ledcWrite(0, 191); // Motor off

  // Setup pump pins
  pinMode(PUMP_IN1_PIN, OUTPUT);
  pinMode(PUMP_IN2_PIN, OUTPUT);
  digitalWrite(PUMP_IN1_PIN, LOW);
  digitalWrite(PUMP_IN2_PIN, LOW);

  // Connect WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected. IP: " + WiFi.localIP().toString());

  // Start WebSocket
  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
  Serial.println("WebSocket server started on port 81");
}

void loop() {
  webSocket.loop();
}

// WebSocket Event Handler
void webSocketEvent(uint8_t clientNum, WStype_t type, uint8_t * payload, size_t length) {
  if (type == WStype_TEXT) {
    String msg = String((char*)payload);
    msg.trim();
    Serial.println("Received: " + msg);
    
    if (msg.startsWith("R-")) {
      int speed = msg.substring(2).toInt();
      speed = constrain(speed, 0, 100);
      int pwm = map(speed, 0, 100, 191, 253);
      ledcWrite(0, pwm);
      currentMotorSpeed = speed;
      webSocket.sendTXT(clientNum, "Motor speed set to " + String(speed) + "%");
    }
    else if (msg.startsWith("V-")) {
      int vol = msg.substring(2).toInt();
      int duration = (vol * 3000) / 25;
      digitalWrite(PUMP_IN1_PIN, HIGH);
      digitalWrite(PUMP_IN2_PIN, LOW);
      delay(duration);
      digitalWrite(PUMP_IN1_PIN, LOW);
      digitalWrite(PUMP_IN2_PIN, LOW);
      webSocket.sendTXT(clientNum, "Pumped " + String(vol) + " ml of water");
    }
    else if (msg.startsWith("D-")) {
      int delaySec = msg.substring(2).toInt();
      delay(delaySec * 1000);
      webSocket.sendTXT(clientNum, "Delay of " + String(delaySec) + "s completed");
    }
    else {
      webSocket.sendTXT(clientNum, "Invalid command");
    }
  }
}
