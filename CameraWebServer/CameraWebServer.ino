#define CAMERA_MODEL_AI_THINKER  // Most ESP32-CAM modules use AI-Thinker
#include "camera_pins.h"
#include "board_config.h"
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ==== Wi-Fi settings ====
const char* ssid = "shanto";
const char* password = "shanto.py";

// ==== Web Server ====
WebServer server(80);

// ==== Camera config ====
void startCameraServer();

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
  
  // *** SUGGESTION 1: Use 20MHz for more stability ***
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  config.frame_size = FRAMESIZE_VGA;    // 640x480
  
  // *** SUGGESTION 2: Corrected comment ***
  config.jpeg_quality = 10;             // 0-63 (0=worst, 63=best)
  config.fb_count = 2; // Use 2 for streaming, 1 if you run out of RAM

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

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
  // *** FIX 1: Add server.handleClient() ***
  server.handleClient();
}

// ==== MJPEG streaming handler ====
void handle_jpeg_stream() {
  WiFiClient client = server.client();
  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
  client.print(response);

  // *** FIX 2: Add client.connected() check ***
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

    // delay(83); // ~12 FPS
  }
  
  Serial.println("Client disconnected from stream.");
}

void startCameraServer() {
  server.on("/stream", HTTP_GET, handle_jpeg_stream);
  server.begin();
}