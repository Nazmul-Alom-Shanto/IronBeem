#define CAMERA_MODEL_AI_THINKER  // Most ESP32-CAM modules use AI-Thinker
#include "camera_pins.h"
#include "board_config.h"
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ==== Wi-Fi settings ====
const char* ssid = "shanto";
const char* password = "shanto.py";

// ==== ✅ NEW: LED PWM Constants ====
// The white flash LED is on GPIO 4
const int LED_PIN = 4;
// Use channel 1 for the LED (channel 0 is used by the camera)
const int LEDC_CHANNEL = 1; 
const int LEDC_RESOLUTION = 8; // 8-bit resolution (0-255)
const int LEDC_FREQ = 5000;    // 5kHz PWM frequency

// ==== Web Server ====
WebServer server(80);

// ==== Function Declarations ====
void startCameraServer();
void handle_jpeg_stream();
void handle_led_control(); // ✅ NEW

// ==== Setup ====
void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;    // 640x480
  config.jpeg_quality = 10;
  config.fb_count = 2;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // ==== ✅ NEW: LED PWM Setup ====
  Serial.println("Setting up LED PWM...");
  // Configure the PWM channel
  ledcSetup(LEDC_CHANNEL, LEDC_FREQ, LEDC_RESOLUTION);
  // Attach the LED pin to the PWM channel
  ledcAttachPin(LED_PIN, LEDC_CHANNEL);
  // Turn the LED off on boot
  ledcWrite(LEDC_CHANNEL, 0);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Camera Stream Ready! Go to: http://");
  Serial.println(WiFi.localIP());

  startCameraServer();
}

// ==== Loop ====
void loop() {
  server.handleClient();
}

// ==== ✅ NEW: LED Control Handler ====
void handle_led_control() {
  int level = 0; // Default to 0 (off)
  
  // Check if the "level" parameter exists in the URL
  if (server.hasArg("level")) {
    level = server.arg("level").toInt();
    
    // Clamp the value to the valid 0-255 range
    if (level < 0) level = 0;
    if (level > 255) level = 255;
    
    Serial.printf("Setting LED brightness to: %d\n", level);
    
    // Write the brightness value to the PWM channel
    ledcWrite(LEDC_CHANNEL, level);
    
    server.send(200, "text/plain", "OK, LED set to " + String(level));
  } else {
    // If "level" parameter is missing
    Serial.println("Missing 'level' parameter");
    server.send(400, "text/plain", "Missing 'level' parameter (e.g., /led?level=100)");
  }
}

// ==== MJPEG streaming handler ====
void handle_jpeg_stream() {
  WiFiClient client = server.client();
  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
  client.print(response);

  while (client.connected()) {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      continue;
    }

    client.printf("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);
    client.write(fb->buf, fb->len);   
    client.print("\r\n");
    esp_camera_fb_return(fb);
  }
  Serial.println("Client disconnected from stream.");
}

void startCameraServer() {
  server.on("/stream", HTTP_GET, handle_jpeg_stream);
  
  // ==== ✅ NEW: Register the LED handler ====
  server.on("/led", HTTP_GET, handle_led_control);
  
  server.begin();
}