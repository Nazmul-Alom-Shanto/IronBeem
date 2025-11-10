/*
 * AI-Powered Laser Turret - Component 3: The "Hands"
 * MCU: ESP32
 * Role: Receives ABSOLUTE angles (pan, tilt) and
 * drives two servos + a laser diode.
 *
 * ===== CHANGELOG =====
 * - Refactored /aim to accept absolute pan/tilt angles.
 * - Removed all gain/correction logic from ESP32.
 * - All P-control logic is now on the Python 'Brain'.
 * - Kept safety clamping.
 */
// ========== LIBRARIES ==========
#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <math.h> 

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

// Initial angles (tracks current state)
int panAngle  = 90;
int tiltAngle = 90;

// Limits (Safety clamp)
const int MIN_ANGLE = 10;
const int MAX_ANGLE = 170; // Safe limit for 180-deg servos

// ❌ REMOVED: GAIN constants are now in Python

// Web server
WebServer server(80);

// ========== PERFORMANCE LOGGING ==========
unsigned long lastRequestTime = 0; 

// ========== COLOR LOGS ==========
#define RED     "\033[31m"
#define GREEN   "\033[32m"
#define YELLOW  "\033[33m"
#define BLUE    "\033[34m"
#define CYAN    "\033[36m"
#define MAGENTA "\033[35m" 
#define RESET   "\033[0m"

// ===================== CLAMP ANGLES =====================
int clampAngle(int value) {
  // Uses our new MIN/MAX ANGLE constants
  if (value < MIN_ANGLE) return MIN_ANGLE;
  if (value > MAX_ANGLE) return MAX_ANGLE;
  return value;
}


// ===================== AIM HANDLER (✅ MODIFIED) =====================
void handleAim() {
  // --- 1. Performance Timing ---
  unsigned long startTime = micros(); 
  float timeSinceLastMs = (startTime - lastRequestTime) / 1000.0; 
  float rps = 1000.0 / timeSinceLastMs; 
  lastRequestTime = startTime; 

  // --- 2. Request Logging ---
  String clientIP = server.client().remoteIP().toString();
  Serial.printf(CYAN "\n=== /aim REQUEST from %s ===\n" RESET, clientIP.c_str());
  Serial.printf(MAGENTA " > Perf: %.2f ms since last (%.1f RPS)\n" RESET, timeSinceLastMs, rps);
  
  // --- 3. Get Absolute Angle Inputs ---
  if (!server.hasArg("pan") || !server.hasArg("tilt")) {
    Serial.println(RED "[ERROR] Missing pan or tilt parameters!" RESET);
    server.send(400, "text/plain", "Missing pan or tilt parameter");
    return;
  }
  
  int newPan  = server.arg("pan").toInt();
  int newTilt = server.arg("tilt").toInt();
  Serial.printf(YELLOW " > Input Angles: PAN=%d, TILT=%d\n" RESET, newPan, newTilt);

  // ❌ REMOVED: All correction, gain, and float math is gone.

  // --- 4. Store old angles (for logging) & Apply Safety Clamp ---
  int oldPan  = panAngle;
  int oldTilt = tiltAngle;
  
  // We trust Python, but clamp just in case for safety
  panAngle  = clampAngle(newPan);
  tiltAngle = clampAngle(newTilt);

  // --- 5. Move Servos ---
  panServo.write(panAngle);
  tiltServo.write(tiltAngle);

  // --- 6. Final Log ---
  Serial.printf(GREEN " > Servo Output: PAN %d -> %d | TILT %d -> %d\n" RESET, 
                oldPan, panAngle, oldTilt, tiltAngle);
                
  server.send(200, "text/plain", "OK");
  unsigned long duration = micros() - startTime;
  Serial.printf(MAGENTA " > Request processing time: %lu us\n" RESET, duration);
}


// ===================== LASER HANDLER =====================
// (This function is unchanged)
void handleLaser() {
  lastRequestTime = micros(); 
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
// (This function is unchanged)
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
  Serial.println(YELLOW "Servos centered." RESET);

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
  
  lastRequestTime = micros();
}

// ===================== LOOP =====================
// (This function is unchanged)
void loop() {
  server.handleClient();
}