/*
 * AI-Powered Laser Turret - Component 3: The "Hands"
 * MCU: ESP32
 * Role: Receives aiming commands (error_x, error_y) and
 * drives two servos + a laser diode.
 *
 * ===== CHANGELOG =====
 * - Fixed MAX_ANGLE from 360 to 170 (common servos are 0-180)
 * - Added Client IP to logs for more detail
 * - Added detailed performance logging (Time Since Last, RPS)
 * - Changed angle math to use round() instead of floor()
 * =======================
 */

// ========== LIBRARIES ==========
#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <math.h> // ««« ADDED: For round()

// ========== WIFI SETTINGS ==========
const char* ssid     = "shanto";
const char* password = "shanto.py";

// ========== HARDWARE PINS ==========
const int PAN_SERVO_PIN  = 25;
const int TILT_SERVO_PIN = 26;
const int LASER_PIN       = 27;

// ========== SERVOS ==========
Servo panServo;
Servo tiltServo;

// Initial angles
int panAngle  = 90;
int tiltAngle = 60;

// Limits
const int MIN_ANGLE = 10;
const int MAX_ANGLE = 170; // Safe limit for 180-deg servos

// Tuning (direction depends on your turret orientation)
float PAN_GAIN  = 0.0225;
float TILT_GAIN = -0.0225; // Negative gain flips the direction

// Web server
WebServer server(80);

// ========== PERFORMANCE LOGGING ==========
unsigned long lastRequestTime = 0; // ««« ADDED: For RPS calculation

// ========== COLOR LOGS ==========
#define RED     "\033[31m"
#define GREEN   "\033[32m"
#define YELLOW  "\033[33m"
#define BLUE    "\033[34m"
#define CYAN    "\033[36m"
#define MAGENTA "\033[35m" // ««« ADDED: For new logs
#define RESET   "\033[0m"


// ===================== CLAMP ANGLES =====================
int clampAngle(int value) {
  // Uses our new MIN/MAX ANGLE constants
  if (value < MIN_ANGLE) return MIN_ANGLE;
  if (value > MAX_ANGLE) return MAX_ANGLE;
  return value;
}


// ===================== AIM HANDLER =====================
void handleAim() {
  // --- 1. Performance Timing ---
  unsigned long startTime = micros(); // For processing time
  float timeSinceLastMs = (startTime - lastRequestTime) / 1000.0; // ««« ADDED
  float rps = 1000.0 / timeSinceLastMs; // ««« ADDED
  lastRequestTime = startTime; // ««« ADDED: Reset timer

  // --- 2. Request Logging ---
  String clientIP = server.client().remoteIP().toString();
  Serial.printf(CYAN "\n=== /aim REQUEST from %s ===\n" RESET, clientIP.c_str());
  
  // --- ««« ADDED: Log timing stats ---
  Serial.printf(MAGENTA " > Perf: %.2f ms since last (%.1f RPS)\n" RESET, timeSinceLastMs, rps);

  if (!server.hasArg("x") || !server.hasArg("y")) {
    Serial.println(RED "[ERROR] Missing x or y parameters!" RESET);
    server.send(400, "text/plain", "Missing x or y parameter");
    return;
  }

  // --- 3. Get Error Inputs ---
  int errorX = server.arg("x").toInt();
  int errorY = server.arg("y").toInt();
  Serial.printf(YELLOW " > Input Errors: X=%d, Y=%d\n" RESET, errorX, errorY);

  // Store old angles for more meaningful logs
  int oldPan  = panAngle;
  int oldTilt = tiltAngle;

  // --- 4. Proportional Control (Float Math) ---
  float panCorrection  = errorX * PAN_GAIN;
  float tiltCorrection = errorY * TILT_GAIN;

  // Calculate new float angles BEFORE rounding
  float floatPanAngle  = (float)panAngle  - panCorrection;
  float floatTiltAngle = (float)tiltAngle - tiltCorrection;
  
  // --- ««« ADDED: Log detailed float math ---
  Serial.printf(BLUE " > Float Math: pan(%.2f - %.2f = %.2f) tilt(%.2f - %.2f = %.2f)\n" RESET,
                (float)oldPan, panCorrection, floatPanAngle,
                (float)oldTilt, tiltCorrection, floatTiltAngle);

  // --- 5. Apply round() and Convert to Integer ---
  // ««« MODIFIED: Use round() as requested ---
  panAngle  = (int)round(floatPanAngle);
  tiltAngle = (int)round(floatTiltAngle);

  // --- 6. Clamp Angles ---
  panAngle  = clampAngle(panAngle);
  tiltAngle = clampAngle(tiltAngle);

  // --- 7. Move Servos ---
  panServo.write(panAngle);
  tiltServo.write(tiltAngle);

  // --- 8. Final Log ---
  Serial.printf(GREEN " > Servo Output: PAN %d -> %d | TILT %d -> %d\n" RESET, 
                oldPan, panAngle, oldTilt, tiltAngle);

  server.send(200, "text/plain", "OK");

  unsigned long duration = micros() - startTime;
  Serial.printf(MAGENTA " > Request processing time: %lu us\n" RESET, duration);
}



// ===================== LASER HANDLER =====================
void handleLaser() {
  lastRequestTime = micros(); // ««« ADDED: Reset timer to keep RPS accurate
  String clientIP = server.client().remoteIP().toString();

  Serial.printf(CYAN "\n=== /laser REQUEST from %s ===\n" RESET, clientIP.c_str());

  if (!server.hasArg("state")) {
    Serial.println(RED "[ERROR] Missing state parameter!" RESET);
    server.send(400, "text/plain", "Missing state parameter");
    return;
  }

  String state = server.arg("state");

  if (state == "on") {
    digitalWrite(LASER_PIN, HIGH);
    Serial.println(GREEN " > Laser: ON" RESET);
  } 
  else {
    digitalWrite(LASER_PIN, LOW);
    Serial.println(YELLOW " > Laser: OFF" RESET);
  }

  server.send(200, "text/plain", "Laser set to " + state);
}



// ===================== SETUP =====================
void setup() {
  Serial.begin(115200);
  Serial.println("\n\nBooting 'Hands' Controller...");

  // Hardware setup
  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, LOW);
  
  // Allow allocation of all timers
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  panServo.attach(PAN_SERVO_PIN);
  tiltServo.attach(TILT_SERVO_PIN);

  // Center servos on boot
  panServo.write(panAngle);
  tiltServo.write(tiltAngle);
  Serial.println(YELLOW "Servos centered at 90 deg." RESET);

  // WiFi
  Serial.println(BLUE "\nConnecting to WiFi..." RESET);
  WiFi.begin(ssid, password);

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    retry++;
    if (retry % 16 == 0) Serial.println();
  }

  Serial.println(GREEN "\n✅ WiFi Connected!" RESET);
  Serial.printf(GREEN "IP Address: %s\n" RESET, WiFi.localIP().toString().c_str());

  // Web routes
  server.on("/aim", HTTP_GET, handleAim);
  server.on("/laser", HTTP_GET, handleLaser);

  server.begin();
  Serial.println(GREEN "✅ HTTP Server started! Waiting for commands..." RESET);
  
  lastRequestTime = micros(); // ««« ADDED: Initialize the timer
}



// ===================== LOOP =====================
void loop() {
  server.handleClient();
}