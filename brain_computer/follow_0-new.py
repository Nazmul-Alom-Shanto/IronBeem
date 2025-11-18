import cv2
import time
import numpy as np
import mediapipe as mp 
import math
import websocket # ✅ Using WebSockets for ALL commands 
from collections import deque # ✅ More efficient way to track frame times
import cv2.aruco as aruco


# --- 1. CONSTANTS ---
EYE_STREAM_URL = "http://10.42.0.176/stream"
HANDS_WS_URL = "ws://10.42.0.164:81" 

# --- 2. TUNING PARAMETERS ---
FIRE_THRESHOLD_PX = 40
# ✅ WARNING: Setting this to 0.0 WILL cause the laser to
# flicker rapidly. Recommend 0.1 or 0.2 for a stable "lock-on".
FIRE_TIME_SECONDS = 0 # ✅ Changed from 0.0 to prevent flicker
# ❌ Removed laser off delay
# ❌ SMOOTH_FACTOR has been removed for direct control.

# --- 3. STATE VARIABLES ---
laser_state = "off"
on_target_since = None
# ❌ Removed target_lost_time
center_x = 320 // 2
center_y = 240 // 2

# --- PERFORMANCE PROFILE ---
# ✅ Use a deque for efficient profiling. It never grows past 200 items.
frame_times = deque(maxlen=200)

# --- 4. MediaPipe Setup ---
print("Initializing MediaPipe Hands...")
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.25
)
mp_drawing = mp.solutions.drawing_utils
TARGET_LANDMARK = mp_hands.HandLandmark.MIDDLE_FINGER_MCP
print("MediaPipe Hands initialized.")

# --- 5. SERVO CONTROL STATE & GAINS ---
PAN_GAIN  = 0.02  
TILT_GAIN = -0.021
# ✅ NEW: Hard-stop safety limits in Python
PAN_MIN = 5
PAN_MAX = 175
TILT_MIN = 20
TILT_MAX = 100
# These are still needed to calculate the *next* position
current_pan_angle = 90.0  
current_tilt_angle = 60.0 

# --- 4. ArUco Setup ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)
TARGET_ID = 0
# ❌ Removed old generic clamp_angle function

# --- 6. OVERLAY FUNCTION ---
def draw_stats_overlay(frame, fps, frame_time, min_t, avg_t, max_t):
    y = 22
    step = 22
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    y += step
    cv2.putText(frame, f"Frame: {frame_time:.1f} ms", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    y += step
    cv2.putText(frame, f"Min/Avg/Max: {min_t:.1f}/{avg_t:.1f}/{max_t:.1f} ms", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,0), 2)
    y += step
    cv2.putText(frame, f"Pan/Tilt: {current_pan_angle:.1f}/{current_tilt_angle:.1f}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,255), 2)

# --- 7. Helper: Safe WebSocket Send ---
def ws_send(ws_conn, message):
    try:
        ws_conn.send(message)
    except Exception as e:
        print(f"WS send error: {e}. Reconnecting...")
        try:
            ws_conn.close()
            ws_conn = websocket.create_connection(HANDS_WS_URL)
            ws_conn.send(message) # Retry send
            print("Reconnected.")
        except Exception as e2:
            print(f"Reconnect failed: {e2}")
            time.sleep(1)
    return ws_conn # Return new/old connection

# --- 8. Initialize Stream & WebSocket ---
cap = cv2.VideoCapture(EYE_STREAM_URL)
if not cap.isOpened():
    print("❌ Could not open video stream.")
    exit()
print("✅ Stream opened.")

try:
    print(f"Connecting to WebSocket at {HANDS_WS_URL}...")
    ws = websocket.create_connection(HANDS_WS_URL)
    print("✅ WebSocket connected.")
except Exception as e:
    print(f"❌ WebSocket connection failed: {e}")
    exit()

ws = ws_send(ws, "90,60")
print("✅ Sent initial servo reset command via WebSocket.")

window_name = "Iron Beam Brain (Fast Tracking)"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, 960, 720) 

# --- MAIN LOOP ---
while True:
    loop_start = time.time()
    success, frame = cap.read()
    if not success:
        print("Dropped frame. Reconnecting...")
        cap.release()
        time.sleep(0.5)
        cap = cv2.VideoCapture(EYE_STREAM_URL)
        continue

    h, w, _ = frame.shape
    center_x, center_y = w//2   - 15 , h//2 + 25
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)

    target_found = False
    error_x = 0
    error_y = 0

    # === ARUCO DETECTION ===
    if ids is not None:
        for i, corner in zip(ids.flatten(), corners):
            if i == TARGET_ID:
                target_found = True
                c = corner[0].astype(int)

                target_x = int(np.mean(c[:, 0]))
                target_y = int(np.mean(c[:, 1]))

                error_x = target_x - center_x
                error_y = target_y - center_y

                aruco.drawDetectedMarkers(frame, [corner], np.array([[i]]))
                cv2.circle(frame, (target_x, target_y), 10, (0,0,255), -1)

                break

    # === ✅ WEBSOCKET AIM COMMAND (ROBUST, NO SMOOTHING) ===
    if target_found:
        # 1. Calculate the new target angle
        new_pan_angle  = current_pan_angle  - (error_x * PAN_GAIN)
        new_tilt_angle = current_tilt_angle - (error_y * TILT_GAIN)
        
        # 2. ✅ CLAMP THE STATE to prevent "wind-up" bug
        current_pan_angle = max(PAN_MIN, min(PAN_MAX, new_pan_angle))
        current_tilt_angle = max(TILT_MIN, min(TILT_MAX, new_tilt_angle))
        
        # 3. Round for sending (no 2nd clamp needed)
        pan_int  = int(round(current_pan_angle))
        tilt_int = int(round(current_tilt_angle))
        
        # 4. Send command
        # print("the new position is: (pan, tilt) = (", pan_int, "," , tilt_int, ")" )
        ws = ws_send(ws, f"{pan_int},{tilt_int}")


    # === ✅ SIMPLIFIED WEBSOCKET LASER LOGIC (NO DELAY) ===
    is_on_target = target_found and abs(error_x) < FIRE_THRESHOLD_PX and abs(error_y) < FIRE_THRESHOLD_PX
    now = time.time()
    
    if is_on_target:
        # --- Target is ACQUIRED ---
        
        # 1. Start the "ON" timer if this is the first frame on target
        if on_target_since is None:
            on_target_since = now
        
        # 2. Check if "ON" timer has expired
        if (now - on_target_since) > FIRE_TIME_SECONDS:
            # Timer has expired, we are cleared to fire.
            if laser_state == "off":
                # Only send command if not already on
                ws = ws_send(ws, "laser_on")
                print("LASER: ON")
                laser_state = "on"
    
    else:
        # --- Target is LOST ---
        
        # 1. Reset the "ON" timer
        on_target_since = None
        
        # 2. Turn laser off if it's on
        if laser_state == "on":
            ws = ws_send(ws, "laser_off")
            print("LASER: OFF")
            laser_state = "off"


    # === DRAWING & PROFILING ===
    cv2.line(frame, (center_x, 0), (center_x, h), (0,255,0), 1)
    cv2.line(frame, (0, center_y), (w, center_y), (0,255,0), 1)
    cv2.rectangle(frame,
                  (center_x-FIRE_THRESHOLD_PX, center_y-FIRE_THRESHOLD_PX),
                  (center_x+FIRE_THRESHOLD_PX, center_y+FIRE_THRESHOLD_PX),
                  (0,255,255), 1)

    frame_time = (time.time() - loop_start) * 1000
    frame_times.append(frame_time) # Deque handles max length automatically
    
    if len(frame_times) >= 3:
        recent = frame_times # No need to slice, deque is already capped
        min_t = min(recent)
        max_t = max(recent)
        avg_t = sum(recent) / len(recent)
        fps = 1000.0 / avg_t if avg_t > 0 else 0
    else:
        min_t = max_t = avg_t = frame_time
        fps = 0
    
    draw_stats_overlay(frame, fps, frame_time, min_t, avg_t, max_t) 
    cv2.imshow(window_name, frame)

    # === KEY INPUT ===
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("Quitting...")
        break

# --- CLEANUP ---
print("Cleaning up resources...")
print("Turning laser off.")
ws = ws_send(ws, "laser_off")

ws.close()
cap.release()
cv2.destroyAllWindows()
hands.close()
time.sleep(0.5) 
print("Exiting.")