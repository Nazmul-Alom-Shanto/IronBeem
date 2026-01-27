/*
   ESP32 "Hands" Controller - UNIFIED WebSocket Version (Improved)
   
   This version includes:
   1. ✅ Hard-Stop Safety Limits for servos.
   2. ✅ Anti-Jitter logic (only writes on change).
   3. ✅ Fixed-size buffer for WebSocket to prevent crashes.
*/

#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ESP32Servo.h>

// --- WiFi Credentials ---
const char* ssid = "shanto";
const char* password = "shanto.py";

// --- ✅ Servo Safety Limits (HARD STOPS) ---
// The controller will IGNORE any command outside these bounds.
const int PAN_MIN = 5;
const int PAN_MAX = 175;
const int TILT_MIN = 20;
const int TILT_MAX = 100;

// --- ✅ Initial Positions (Must be within safe limits) ---
const int PAN_START = 90;   // 90 is within 5-175
const int TILT_START = 60;  // 60 is within 20-100

// --- WebSocket Server ---
WebSocketsServer webSocket = WebSocketsServer(81);
// ✅ Set a max command length. Prevents buffer overflow crashes.
// "175,100" is 7 chars. "laser_on" is 8. 32 is very safe.
const int MAX_COMMAND_LENGTH = 32;

// --- Servos ---
Servo panServo;
Servo tiltServo;
int panPin = 26;
int tiltPin = 27;

// --- ✅ Servo State (for reducing jitter) ---
// We store the last written value to avoid re-sending
// the same command, which can cause servo buzz.
// -1 forces the first write in setup().
int currentPan = -1;
int currentTilt = -1;

// --- Laser ---
int laserPin = 14;

// ✅ UNIFIED WebSocket Event Handler (Improved)
void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {

  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[%u] Disconnected!\n", num);
      break;

    case WStype_CONNECTED: {
        IPAddress ip = webSocket.remoteIP(num);
        Serial.printf("[%u] Connected from %d.%d.%d.%d url: %s\n", num, ip[0], ip[1], ip[2], ip[3], payload);
      }
      break;

    case WStype_TEXT: {
        // --- ✅ Robust, High-Speed Command Parser ---

        // 1. Check for command length to prevent crash
        if (length == 0 || length > MAX_COMMAND_LENGTH) {
          Serial.println("Empty or invalid command, ignoring.");
          return;
        }

        // 2. Create a null-terminated C-string from the payload
        char msg[MAX_COMMAND_LENGTH + 1];
        strncpy(msg, (const char *)payload, length);
        msg[length] = '\0';
  
        // 3. Check for an "aim" command (which contains a comma)
        char* comma = strchr(msg, ',');
        
        if (comma != NULL) {
          // --- AIM COMMAND ---
          // It's an aim command like "92,60"
          
          *comma = '\0'; // Split the string by replacing ',' with null
          int panVal = atoi(msg);
          int tiltVal = atoi(comma + 1);
  
          // 4. ✅ Apply safety limits (Hard Stops)
          // We use max/min to "clamp" the value into the safe range.
          int safePan = max(PAN_MIN, min(PAN_MAX, panVal));
          int safeTilt = max(TILT_MIN, min(TILT_MAX, tiltVal));

          // 5. ✅ Write to servos (Anti-Jitter Logic)
          // Only send the command if the position has changed.
          if (safePan != currentPan) {
            panServo.write(safePan);
            Serial.println("pan is at ");
            Serial.println(safePan);
            Serial.println("Right Now \n");

            currentPan = safePan; // Store new position
          }
          if (safeTilt != currentTilt) {
            tiltServo.write(safeTilt);
            Serial.println("tilt is at ");
            Serial.println(safeTilt);
            Serial.println("Right Now \n");
            currentTilt = safeTilt; // Store new position
          }
          
        } else {
          // --- LASER COMMAND ---
          // No comma, check for laser commands
          
          if (strcmp(msg, "laser_on") == 0) {
            Serial.println("Laser ON");
            digitalWrite(laserPin, HIGH);
          } 
          else if (strcmp(msg, "laser_off") == 0) {
            Serial.println("Laser OFF");
            digitalWrite(laserPin, LOW);
          }
          else {
            Serial.printf("Unknown command: %s\n", msg);
          }
        }
      }
      break;
  }
}

void setup() {
  Serial.begin(115200);

  // --- Init Servos ---
  panServo.setPeriodHertz(50);
  tiltServo.setPeriodHertz(50);
  panServo.attach(panPin, 500, 2500);
  tiltServo.attach(tiltPin, 500, 2500);

  // --- Init Laser ---
  pinMode(laserPin, OUTPUT);
  digitalWrite(laserPin, LOW); // Ensure laser is off at boot
 
  // --- Connect to WiFi ---
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP()); // <-- This is the IP you need

  // --- Start WebSocket Server ---
  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
  Serial.println("Unified WebSocket server started on port 81.");

  // --- Set initial position ---
  panServo.write(PAN_START);
  tiltServo.write(TILT_START);
  currentPan = PAN_START;   // ✅ Store the initial state
  currentTilt = TILT_START; // ✅ Store the initial state
  Serial.println("Servos set to safe starting position.");
}

void loop() {
  // ✅ Only one server to loop!
  webSocket.loop();       // Handles all WebSocket traffic
  
  // No delay()! This loop runs as fast as possible.
}