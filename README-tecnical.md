
---

# **AroGuard**

### *Real-Time Computer Vision Tracking System*

### *Fast, Accurate, and Built for Real-World Applications*

---

## **1. What Is AroGuard?**

**A next-generation tracking turret** that uses image recognition to detect, track, and aim at moving objects in real time.

Think of it as:

* **The Eye:** The camera
* **The Brain:** The computer vision system
* **The Hands:** The robotic turret

The goal was simple:
**Make it feel instant — no lag, no delay, no missed targets.**

---

## **2. Why This System Matters**

Traditional DIY turrets are slow and inaccurate due to latency.

**AroGuard solves that**, enabling applications such as:

### **Potential Applications**

* **Air Defense:**
  Radar struggles with very low-altitude drones. Vision-based systems can complement radar.

* **Pest Control for Agriculture:**
  Automatically identify and neutralize harmful insects or pests.

* **Mosquito Control:**
  Vision-guided laser mosquito detection — similar to scientific prototypes.

* **Object-Following Robotics:**
  Any robot that needs fast visual feedback.

---

## **3. System Overview**

### **Distributed Architecture (Key Innovation)**

To maximize speed, the system is split into three independent units:

1. **ESP32-CAM (Eye)**
   Streams live video.

2. **Laptop (Brain)**
   Runs Python + OpenCV + MediaPipe for object detection and tracking.

3. **ESP32 Servo Controller (Hands)**
   Moves the turret and fires the laser.

**Why this Matters:**
Each device focuses on *one job*. No overload, no bottleneck.

---

## **4. Data Flow (Simplified)**

### **Video → Processing → Movement**

* ESP32-CAM streams MJPEG video over TCP.
* Laptop reads the stream, detects target, calculates angle.
* Laptop sends servo commands via a WebSocket connection.
* ESP32 Servo Controller moves instantly.

This structure gives **smooth 30+ FPS tracking** even on low-cost hardware.

---

## **5. Computer Vision Core**

### **Software Stack**

* **Python**
* **OpenCV**
* **MediaPipe (Hand or Object Landmarks)**

### **How Tracking Works**

1. Frame arrives (320×240 for speed).
2. MediaPipe detects key landmarks.
3. Target selected (e.g., center of a hand, object marker).
4. System calculates how far the target is from center.
5. Outputs correction angles for pan & tilt.

**Why QVGA?**
Cut processing time by ~3× with almost no loss of accuracy.

---

## **6. The Latency Problem (The Big Bottleneck)**

### **Initial Method: HTTP Commands**

Each movement command was sent as an HTTP GET request.

**What went wrong:**

* Each command opened a new connection
* ~100ms overhead per update
* Tracking dropped to **3.4 FPS**
* Laser was always behind the hand

This was the biggest technical challenge.

---

## **7. The Breakthrough: WebSockets**

### **Why WebSockets?**

* One permanent connection
* No handshake overhead
* Fast, stable, reliable (TCP)

### **Performance Improvement**

| Protocol   | Commands/sec | Latency    |
| ---------- | ------------ | ---------- |
| HTTP GET   | ~10          | 100–150 ms |
| WebSockets | 100+         | <20 ms     |

The system became *instant* — this is what unlocked real-time tracking.

---

## **8. Smooth Movement Engineering**

Servos normally “jump” to positions.
To make motion feel organic:

### **Software Interpolation**

`NewPos = CurrentPos + (TargetPos - CurrentPos) * 0.2`

This gives:

* High speed when target moves fast
* High precision when target slows
* No overshoot
* No jitter

This is what makes the system look professionally engineered.

---

## **9. Power System Engineering**

### **Problem:**

Servos draw high current → cause voltage drops → ESP32 crashes.

### **Solution: Two Separate Power Domains**

* **Clean 5V** (Power Bank): Cameras + ESP32 controllers
* **Dirty 11.1V** (Battery): Servos only
* **Common Ground** ensures proper signal reference

This completely eliminated random resets and instability.

---

## **10. Why Use TCP Video + WebSocket Commands?**

### **Video uses MJPEG over HTTP/TCP**

* No corrupted frames
* Consistent quality
* Good for detection accuracy

### **Control uses WebSockets**

* Low latency
* Continuous command stream
* Perfect reliability

**Right tool for each job.**

---

## **11. Real-World Performance**

* **Tracking Speed:** 30+ FPS
* **System Latency:** <50ms (feels instant)
* **Accuracy:** Tracks small movements precisely
* **Stability:** No brownouts, no frame drops
* **Cost:** Extremely low compared to industrial systems

---

## **12. Future Upgrades**

* **Kalman Filter Prediction**
  Predict target motion for even lower perceived latency.

* **PID Tuning**
  Smoother, more accurate stabilization.

* **Continuous-Rotation or Stepper Turret**
  Enable 360° coverage.

* **Object Classification**
  Identify type of target (drone, bug, gesture).

---

## **13. Why Not Use a Raspberry Pi?**

* ESP32s cost **$10 total**
* A Pi adds **weight, heat, and cost**
* Laptop provides a powerful CPU without increasing turret complexity
* Distributed system is more scalable

---

## **14. Final Summary**

**You built a system that:**

* Detects objects in real time
* Tracks and aims with high-speed accuracy
* Runs smoothly on inexpensive hardware
* Uses smart architecture to minimize latency
* Demonstrates engineering-level optimization
* Has real-world applications in defense, agriculture, robotics, and automation

This isn’t a toy project —
**It’s a practical, high-performance vision-driven robotics platform.**

---

