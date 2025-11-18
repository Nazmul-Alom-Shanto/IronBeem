import cv2
import time
import numpy as np
import threading
import mediapipe as mp
import statistics
import math
import websocket # ✅ Using WebSockets for ALL commands

# --- 1. CONSTANTS ---
EYE_STREAM_URL = "http://10.42.0.176/stream"
# ✅ ONE URL for all commands
HANDS_WS_URL = "ws://10.42.0.164:81" 

# --- 2. TUNING PARAMETERS ---
FIRE_THRESHOLD_PX = 35
FIRE_TIME_SECONDS = 0.0
SMOOTH_FACTOR = 1
isDebugDone = False 
# --- 3. STATE VARIABLES ---
laser_state = "off"
on_target_since = None
center_x = 320 // 2
center_y = 240 // 2

# --- PERFORMANCE PROFILE ---
frame_times = []
# We don't need send_ok/fail, ws.send() is blocking
# or will throw an exception we can catch.

# --- 4. MediaPipe Setup ---
print("Initializing MediaPipe Hands...")
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils
TARGET_LANDMARK = mp_hands.HandLandmark.MIDDLE_FINGER_MCP
print("MediaPipe Hands initialized.")

# --- 5. SERVO CONTROL STATE & GAINS ---
PAN_GAIN  = 0.02  
TILT_GAIN = -0.022
MIN_ANGLE = 0
MAX_ANGLE = 180
current_pan_angle = 90.0  
current_tilt_angle = 60.0 

def clamp_angle(value):
    return max(MIN_ANGLE, min(MAX_ANGLE, value))

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
# We create a helper to handle disconnects
def ws_send(ws_conn, message):
    try:
        ws_conn.send(message)
    except Exception as e:
        print(f"WS send error: {e}. Reconnecting...")
        try:
            ws_conn.close()
            # This is a bit of a hack in a helper,
            # ideally we'd re-assign ws in the main loop
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

# ✅ NEW: Connect to WebSocket
try:
    print(f"Connecting to WebSocket at {HANDS_WS_URL}...")
    ws = websocket.create_connection(HANDS_WS_URL)
    print("✅ WebSocket connected.")
except Exception as e:
    print(f"❌ WebSocket connection failed: {e}")
    print("Is the ESP32 'Hands' controller running the new UNIFIED code?")
    exit()

# Reset position (we can just send a WS message)
ws = ws_send(ws, "90,60")
print("✅ Sent initial servo reset command via WebSocket.")

window_name = "Iron Beam Brain (Unified WebSocket)"
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
    center_x, center_y = w//2 - 10 , h//2 + 8
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    target_found = False
    error_x = 0
    error_y = 0

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        target_point = hand_landmarks.landmark[TARGET_LANDMARK]
        target_x = int(target_point.x * w)
        target_y = int(target_point.y * h)
        target_found = True
        error_x = target_x - center_x
        error_y = target_y - center_y
        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        cv2.circle(frame, (target_x, target_y), 10, (0,0,255), -1)

    # === WEBSOCKET AIM COMMAND ===
    if target_found:
        target_pan_angle  = current_pan_angle  - (error_x * PAN_GAIN)
        target_tilt_angle = current_tilt_angle - (error_y * TILT_GAIN)
        
        smoothed_pan  = (current_pan_angle  * (1 - SMOOTH_FACTOR)) + (target_pan_angle  * SMOOTH_FACTOR)
        smoothed_tilt = (current_tilt_angle * (1 - SMOOTH_FACTOR)) + (target_tilt_angle * SMOOTH_FACTOR)
        
        pan_int  = clamp_angle(int(math.ceil(smoothed_pan - 0.5)))
        tilt_int = clamp_angle(int(math.ceil(smoothed_tilt - 0.5)))
        
        current_pan_angle = smoothed_pan
        current_tilt_angle = smoothed_tilt

        # Send command via WebSocket
        print("the new position is: (pan, tilt) = (", pan_int, "," , tilt_int, ")" )
        if not isDebugDone:
            ws = ws_send(ws, f"{pan_int},{tilt_int}")
            isDebugDone = True


    # === ✅ NEW: WEBSOCKET LASER LOGIC ===
    is_on_target = target_found and abs(error_x) < FIRE_THRESHOLD_PX and abs(error_y) < FIRE_THRESHOLD_PX
    new_laser_state = "off"
    if is_on_target:
        if on_target_since is None:
            on_target_since = time.time()
        if (time.time() - on_target_since) > FIRE_TIME_SECONDS:
            new_laser_state = "on"
    else:
        on_target_since = None
        
    if new_laser_state != laser_state:
        # ✅ Send "laser_on" or "laser_off" as a string
        if new_laser_state == "on":
            ws = ws_send(ws, "laser_on")
            print("LASER: ON")
        else:
            ws = ws_send(ws, "laser_off")
            print("LASER: OFF")
        laser_state = new_laser_state
    # ws = ws_send(ws, "laser_on")


    # === DRAWING & PROFILING ===
    cv2.line(frame, (center_x, 0), (center_x, h), (0,255,0), 1)
    cv2.line(frame, (0, center_y), (w, center_y), (0,255,0), 1)
    cv2.rectangle(frame,
                  (center_x-FIRE_THRESHOLD_PX, center_y-FIRE_THRESHOLD_PX),
                  (center_x+FIRE_THRESHOLD_PX, center_y+FIRE_THRESHOLD_PX),
                  (0,255,255), 1)

    frame_time = (time.time() - loop_start) * 1000
    frame_times.append(frame_time)
    if len(frame_times) >= 3:
        recent = frame_times[-200:]
        min_t = min(recent)
        max_t = max(recent)
        avg_t = sum(recent) / len(recent)
        fps = 1000.0 / avg_t if avg_t > 0 else 0
    else:
        min_t = max_t = avg_t = frame_time
        fps = 0
    # Removed ok/fail, since we don't track that anymore
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