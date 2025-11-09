/*
 * AI-Powered Laser Turret - Component 3: The "Hands"
 * MCU: NodeMCU 1.0 (ESP8266)
 * Role: This script is the "robot body." It obeys commands
 * from the "Brain" (Laptop) to move servos and fire the laser.
 *
 * --- VERSION: Added /testpan and /testtilt routes for debugging ---
*/

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Servo.h>

// --- 1. WIFI CREDENTIALS ---
// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
// !!! ENTER YOUR WIFI SSID AND PASSWORD  !!!
// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
const char* ssid = "403";
const char* password = "vewjp98479";
// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


// --- 2. HARDWARE PINS ---
// (You can change these)
const int PAN_SERVO_PIN = D1;  // Servo for X-axis (left/right)
const int TILT_SERVO_PIN = D2; // Servo for Y-axis (up/down)
const int LASER_PIN = D5;      // Signal pin for the laser module
const int TEST_PIN = D3;       // User's test pin

// --- 3. TUNING PARAMETERS (IMPORTANT!) ---
// These "P-Gains" control *how fast* the servo reacts to the error.
// - Start with SMALL values (like 0.05).
// - If the turret is too slow, increase it slightly (e.g., 0.08).
// - If the turret overshoots and "wobbles," decrease it.
const float KP_PAN = 1; // Proportional gain for Pan (X-axis)

// ** Y-Axis might be inverted! **
// If the turret moves UP when the hand is DOWN, make this negative.
const float KP_TILT = 1; // Proportional gain for Tilt (Y-axis)

// --- 4. SERVO LIMITS ---
const int MIN_ANGLE = 20;  // Minimum angle for servos (to prevent hitting frame)
const int MAX_ANGLE = 160; // Maximum angle for servos
const int HOME_ANGLE = 90; // Center position

// --- 5. GLOBAL OBJECTS ---
ESP8266WebServer server(80); // Standard HTTP port
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
  Serial.println("\n\n--- NodeMCU 'Hands' Initializing (DEBUG_V2) ---");

  // --- 1. Setup Hardware ---
  Serial.println("[DEBUG] Setting up hardware pins...");
  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, LOW); // Start with laser OFF
  Serial.println("[DEBUG]   > LASER_PIN (D5) set to OUTPUT, LOW");

  pinMode(TEST_PIN, OUTPUT);
  digitalWrite(TEST_PIN, LOW); // Start with test pin OFF
  Serial.println("[DEBUG]   > TEST_PIN (D3) set to OUTPUT, LOW");


  servoPan.attach(PAN_SERVO_PIN);
  servoTilt.attach(TILT_SERVO_PIN);
  Serial.println("[DEBUG]   > Servos attached to pins D1, D2");

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
  // Endpoint 1: /aim
  server.on("/aim", handleAim);
  Serial.println("[DEBUG]   > /aim registered");

  // Endpoint 2: /laser
  server.on("/laser", handleLaser);
  Serial.println("[DEBUG]   > /laser registered");

  // --- NEW: Register Test Endpoints ---
  server.on("/testpan", handleTestPan);
  Serial.println("[DEBUG]   > /testpan registered");

  server.on("/testtilt", handleTestTilt);
  Serial.println("[DEBUG]   > /testtilt registered");
  // ---

  // --- 4. Start Server ---
  server.begin();
  Serial.println("[DEBUG] Web server started.");
  Serial.println("--- 'Hands' are Online ---");
  Serial.print("Commands URL: http://");
  Serial.println(WiFi.localIP());
}

void loop() {
  // This is the only thing needed in the loop.
  // It listens for incoming HTTP requests.
  server.handleClient();
}

/**
 * @brief Handles the /aim command
 * This is the P-Controller (Proportional Controller).
 * It calculates a *correction* based on the error received.
 */
void handleAim() {
  Serial.println("\n[DEBUG] === Endpoint /aim hit ===");

  // Check if we have the required arguments
  if (!server.hasArg("x") || !server.hasArg("y")) {
    Serial.println("[ERROR] Bad Request: Missing x or y");
    server.send(400, "text/plain", "Bad Request: Missing x or y");
    return;
  }

  // Get the error values from the URL
  // error_x > 0 means target is to the RIGHT
  // error_y > 0 means target is BELOW center
  float error_x = server.arg("x").toFloat();
  float error_y = server.arg("y").toFloat();
  Serial.print("[DEBUG]   Raw Error (x, y): (");
  Serial.print(error_x);
  Serial.print(", ");
  Serial.print(error_y);
  Serial.println(")");

  // --- P-Controller Logic ---
  // Calculate the *change* in angle needed
  // This is the "Proportional" part
  float panCorrection = error_x * KP_PAN;
  float tiltCorrection = error_y * KP_TILT;
  Serial.print("[DEBUG]   Correction (pan, tilt): (");
  Serial.print(panCorrection);
  Serial.print(", ");
  Serial.print(tiltCorrection);
  Serial.println(")");

  // Update the current angle
  // We use += so the movement is relative
  currentPanAngle += panCorrection;
  currentTiltAngle += tiltCorrection;
  Serial.print("[DEBUG]   New Unconstrained Angle (pan, tilt): (");
  Serial.print(currentPanAngle);
  Serial.print(", ");
  Serial.print(currentTiltAngle);
  Serial.println(")");

  // --- Constrain & Write ---
  // Clamp the values to stay within our safe limits
  currentPanAngle = constrain(currentPanAngle, MIN_ANGLE, MAX_ANGLE);
  currentTiltAngle = constrain(currentTiltAngle, MIN_ANGLE, MAX_ANGLE);
  Serial.print("[DEBUG]   FINAL Constrained Angle (pan, tilt): (");
  Serial.print((int)currentPanAngle);
  Serial.print(", ");
  Serial.print((int)currentTiltAngle);
  Serial.println(")");

  // Send the final angle to the servos
  servoPan.write((int)currentPanAngle);
  servoTilt.write((int)currentTiltAngle);

  // Send a simple "OK" response
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

// --- NEW TEST FUNCTIONS ---

/**
 * @brief Handles the /testpan command
 * Adds a value to the current pan angle.
 * Listens for: /testpan?angle=10
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
 * Adds a value to the current tilt angle.
 * Listens for: /testtilt?angle=-5
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