/*
 * AI-Powered Laser Turret - Component 3: The "Hands"
 * MCU: ESP32
 * Role: This script is the "robot body." It obeys commands
 * from the "Brain" (Laptop) to move servos and fire the laser.
 *
 * --- VERSION: Fixed attach() function and removed stray text ---
*/

// -- CHANGED -- (Libraries for ESP32)
#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

// --- 1. WIFI CREDENTIALS ---
const char* ssid = "shanto";
const char* password = "shanto.py";


// --- 2. HARDWARE PINS (!!! YOU MUST CHANGE THESE !!!) ---
// (The names D1, D2, etc. do not exist on ESP32)
// (Look at your board and pick new GPIO numbers)
// -- CHANGED --
const int PAN_SERVO_PIN = 25;  // Example: GPIO 25
const int TILT_SERVO_PIN = 26; // Example: GPIO 26
const int LASER_PIN = 27;      // Example: GPIO 27
const int TEST_PIN = 14;       // Example: GPIO 14
// --- LINE 24 "Wake up with purpose" REMOVED ---


// --- 3. TUNING PARAMETERS (IMPORTANT!) ---
const float KP_PAN = 0.05;
const float KP_TILT = 0.05;

// --- 4. SERVO LIMITS ---
const int MIN_ANGLE = 10;
const int MAX_ANGLE = 5000;
const int HOME_ANGLE = 90;

// --- 5. GLOBAL OBJECTS ---
// -- CHANGED -- (Class name is now WebServer)
WebServer server(80);

// -- CHANGED -- (Uses the ESP32Servo library now)
Servo servoPan;
Servo servoTilt;

// Current state variables (in degrees)
float currentPanAngle = HOME_ANGLE;
float currentTiltAngle = HOME_ANGLE;

// --- TEST HANDLER PROTOTYPES ---
void handleTestPan();
void handleTestTilt();


void setup() {
  Serial.begin(115200);
  Serial.println("\n\n--- ESP32 'Hands' Initializing (DEBUG_V3) ---"); // -- CHANGED --

  // --- 1. Setup Hardware ---
  Serial.println("[DEBUG] Setting up hardware pins...");
  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, LOW); // Start with laser OFF
  Serial.printf("[DEBUG]   > LASER_PIN (GPIO %d) set to OUTPUT, LOW\n", LASER_PIN);

  pinMode(TEST_PIN, OUTPUT);
  digitalWrite(TEST_PIN, LOW); // Start with test pin OFF
  Serial.printf("[DEBUG]   > TEST_PIN (GPIO %d) set to OUTPUT, LOW\n", TEST_PIN);

  // --- Setup Servos for ESP32 ---
  // -- CHANGED -- (Using the correct 1-argument attach function)
  // The library will automatically assign the next free PWM channel.
  servoPan.attach(PAN_SERVO_PIN);
  servoTilt.attach(TILT_SERVO_PIN);
  Serial.printf("[DEBUG]   > Servos attached to pins GPIO %d, GPIO %d\n", PAN_SERVO_PIN, TILT_SERVO_PIN);


  // Go to home position
  Serial.print("[DEBUG] Moving servos to home position (");
  Serial.print(HOME_ANGLE);
  Serial.println(" deg)...");
  servoPan.write(currentPanAngle);
  servoTilt.write(currentTiltAngle);
  delay(1000); // Wait for servos to move
  Serial.println("[DEBUG] Servos at home.");

  // --- 2. Connect to Wi-Fi ---
  Serial.printf("[DEBUG] Connecting to WiFi: %s ", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[DEBUG] WiFi connected!");
  Serial.print("[DEBUG] IP Address: ");
  Serial.println(WiFi.localIP());

  // --- 3. Setup Web Server Endpoints ---
  Serial.println("[DEBUG] Registering web server endpoints...");
  server.on("/aim", handleAim);
  Serial.println("[DEBUG]   > /aim registered");

  server.on("/laser", handleLaser);
  Serial.println("[DEBUG]   > /laser registered");

  server.on("/testpan", handleTestPan);
  Serial.println("[DEBUG]   > /testpan registered");

  server.on("/testtilt", handleTestTilt);
  Serial.println("[DEBUG]   > /testtilt registered");

  // --- 4. Start Server ---
  server.begin();
  Serial.println("[DEBUG] Web server started.");
  Serial.println("--- 'Hands' are Online ---");
  Serial.print("Commands URL: http://");
  Serial.println(WiFi.localIP());
}

void loop() {
  server.handleClient();
}

// --- ALL LOGIC BELOW THIS LINE IS IDENTICAL ---
// --- NO CHANGES WERE NEEDED TO THE HANDLERS ---

/**
 * @brief Handles the /aim command
 */
void handleAim() {
  Serial.println("\n[DEBUG] === Endpoint /aim hit ===");

  if (!server.hasArg("x") || !server.hasArg("y")) {
    Serial.println("[ERROR] Bad Request: Missing x or y");
    server.send(400, "text/plain", "Bad Request: Missing x or y");
    return;
  }

  float error_x = server.arg("x").toFloat();
  float error_y = server.arg("y").toFloat();
  Serial.print("[DEBUG]   Raw Error (x, y): (");
  Serial.print(error_x);
  Serial.print(", ");
  Serial.print(error_y);
  Serial.println(")");

  float panCorrection = error_x * KP_PAN;
  float tiltCorrection = error_y * KP_TILT;
  Serial.print("[DEBUG]   Correction (pan, tilt): (");
  Serial.print(panCorrection);
  Serial.print(", ");
  Serial.print(tiltCorrection);
  Serial.println(")");

  currentPanAngle += panCorrection;
  currentTiltAngle += tiltCorrection;
  Serial.print("[DEBUG]   New Unconstrained Angle (pan, tilt): (");
  Serial.print(currentPanAngle);
  Serial.print(", ");
  Serial.print(currentTiltAngle);
  Serial.println(")");

  currentPanAngle = constrain(currentPanAngle, MIN_ANGLE, MAX_ANGLE);
  currentTiltAngle = constrain(currentTiltAngle, MIN_ANGLE, MAX_ANGLE);
  Serial.print("[DEBUG]   FINAL Constrained Angle (pan, tilt): (");
  Serial.print((int)currentPanAngle);
  Serial.print(", ");
  Serial.print((int)currentTiltAngle);
  Serial.println(")");

  servoPan.write((int)currentPanAngle);
  servoTilt.write((int)currentTiltAngle);

  server.send(200, "text/plain", "OK");
  Serial.println("[DEBUG]   > Sent 200/OK response.");
}

/**
 * @brief Handles the /laser command
 */
void handleLaser() {
  Serial.println("\n[DEBUG] === Endpoint /laser hit ===");
  String state = "off";

  if (server.hasArg("state")) {
    state = server.arg("state");
  }
  Serial.print("[DEBUG]   Received state: '");
  Serial.print(state);
  Serial.println("'");

  if (state == "on") {
    digitalWrite(LASER_PIN, HIGH);
    Serial.println("[DEBUG]   > Action: Turning Laser ON");
    server.send(200, "text/plain", "Laser ON");
  } else {
    digitalWrite(LASER_PIN, LOW);
    Serial.println("[DEBUG]   > Action: Turning Laser OFF");
    server.send(200, "text/plain", "Laser OFF");
  }
}

/**
 * @brief Handles the /testpan command
 */
void handleTestPan() {
  Serial.println("\n[DEBUG] === Endpoint /testpan hit ===");
  if (!server.hasArg("angle")) {
    Serial.println("[ERROR] Bad Request: Missing 'angle'");
    server.send(400, "text/plain", "Bad Request: Missing 'angle'");
    return;
  }

  float angleToAdd = server.arg("angle").toFloat();
  Serial.print("[DEBUG]   Received angle to add: ");
  Serial.println(angleToAdd);

  Serial.print("[DEBUG]   Old Pan Angle: ");
  Serial.println(currentPanAngle);

  currentPanAngle += angleToAdd;
  currentPanAngle = constrain(currentPanAngle, MIN_ANGLE, MAX_ANGLE);

  Serial.print("[DEBUG]   NEW Pan Angle: ");
  Serial.println((int)currentPanAngle);

  servoPan.write((int)currentPanAngle);
  server.send(200, "text/plain", "Pan OK");
}

/**
 * @brief Handles the /testtilt command
 */
void handleTestTilt() {
  Serial.println("\n[DEBUG] === Endpoint /testtilt hit ===");
  if (!server.hasArg("angle")) {
    Serial.println("[ERROR] Bad Request: Missing 'angle'");
    server.send(400, "text/plain", "Bad Request: Missing 'angle'");
    return;
  }

  float angleToAdd = server.arg("angle").toFloat();
  Serial.print("[DEBUG]   Received angle to add: ");
  Serial.println(angleToAdd);

  Serial.print("[DEBUG]   Old Tilt Angle: ");
  Serial.println(currentTiltAngle);

  currentTiltAngle += angleToAdd;
  currentTiltAngle = constrain(currentTiltAngle, MIN_ANGLE, MAX_ANGLE);

  Serial.print("[DEBUG]   NEW Tilt Angle: ");
  Serial.println((int)currentTiltAngle);

  servoTilt.write((int)currentTiltAngle);
  server.send(200, "text/plain", "Tilt OK");
}