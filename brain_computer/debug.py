import cv2
import requests
import time
import numpy as np
import threading
import mediapipe as mp
import statistics
import math # ✅ ADDED for round()

# --- 1. CONSTANTS ---
EYE_STREAM_URL = "http://10.42.0.176/stream"
HANDS_URL = "http://10.42.0.164"

# --- 2. TUNING PARAMETERS ---
FIRE_THRESHOLD_PX = 25
FIRE_TIME_SECONDS = 0.0

# --- 3. STATE VARIABLES ---
laser_state = "off"
on_target_since = None
center_x = 320 // 2
center_y = 240 // 2

# --- PERFORMANCE PROFILE ---
frame_times = []
send_ok = 0
send_fail = 0
send_total = 0

# --- 4. MediaPipe Setup ---
print("Initializing MediaPipe Hands...")
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils
TARGET_LANDMARK = mp_hands.HandLandmark.MIDDLE_FINGER_MCP

print("MediaPipe Hands initialized.")

#

# --- 5. ✅ NEW: SERVO CONTROL STATE & GAINS ---
# These values are moved from the ESP32
PAN_GAIN  = 0.04
TILT_GAIN = -0.04 # Negative gain flips the direction

# These must match the ESP32's initial state & limits
MIN_ANGLE = 0
MAX_ANGLE = 180
current_pan_angle = 90.0  # Start at 90 (float for precision)
current_tilt_angle = 60.0 # Start at 60 (float for precision)

def clamp_angle(value):
    """Clamps angle between MIN and MAX"""
    return max(MIN_ANGLE, min(MAX_ANGLE, value))

# ✅ REAL-TIME OVERLAY FUNCTION
def draw_stats_overlay(frame, fps, frame_time, min_t, avg_t, max_t, ok, fail):
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
    cv2.putText(frame, f"OK/FAIL: {ok}/{fail}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,0), 2)
    # ✅ NEW: Show current angles
    y += step
    cv2.putText(frame, f"Pan/Tilt: {current_pan_angle:.1f}/{current_tilt_angle:.1f}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,255), 2)


# --- Helper: Threaded sender ---
def send_command(url):
    global send_ok, send_fail, send_total
    send_total += 1
    try:
        requests.get(url, timeout=0.5)
        send_ok += 1
    except:
        send_fail += 1

# --- Initialize Stream ---
cap = cv2.VideoCapture(EYE_STREAM_URL)
if not cap.isOpened():
    print("❌ Could not open video stream.")
    exit()
print("✅ Stream opened.")

# reseting the servo position
reset_url = f"{HANDS_URL}/aim?pan=90&tilt=60"
threading.Thread(target=send_command, args=(reset_url,), daemon=True).start()
print("✅ Sent initial servo reset command.")

# ✅ ADD THESE LINES TO MAKE THE WINDOW RESIZABLE
window_name = "Iron Beam Brain (Hand Tracker)"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, 960, 720) # 3x scaled (320*3=960, 240*3=720)

isDone = False
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
    center_x, center_y = w//2 + 9, h//2 + 38
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    target_found = False
    error_x = 0
    error_y = 0

    # === MEDIAPIAPE HAND LANDMARKS ===
    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        target_point = hand_landmarks.landmark[TARGET_LANDMARK]
        target_x = int(target_point.x * w)
        target_y = int(target_point.y * h)
        target_found = True
        error_x = target_x - center_x
        error_y = target_y - center_y
        # Draw hand & fingertip
        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        cv2.circle(frame, (target_x, target_y), 10, (0,0,255), -1)


    # === ✅ MODIFIED: SEND AIM COMMAND ===
    if target_found:
        # 1. Calculate correction (like ESP32 did)
        pan_correction  = error_x * PAN_GAIN
        tilt_correction = error_y * TILT_GAIN

        # 2. Calculate new float angle (matching ESP32's `val - correction`)
        float_pan_angle  = current_pan_angle  - pan_correction
        float_tilt_angle = current_tilt_angle - tilt_correction

        # 3. Round, convert to int, and clamp
        # (This is the exact logic from the ESP32, now in Python)
        pan_int  = clamp_angle(int(math.ceil(float_pan_angle - 0.5))) # Fast round()
        tilt_int = clamp_angle(int(math.ceil(float_tilt_angle - 0.5)))# Fast round()
        
        # 4. Update our state variables
        # We store the *clamped* value as our new state
        current_pan_angle = float(pan_int)
        current_tilt_angle = float(tilt_int)

        # 5. Send the FINAL angles, not the error
        url = f"{HANDS_URL}/aim?pan={pan_int}&tilt={tilt_int}"
        print(url)
        if not isDone:
            threading.Thread(target=send_command, args=(url,), daemon=True).start()
            isDone = True


    # === LASER LOGIC ===
    # (This logic is unchanged, still works perfectly)
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
        url = f"{HANDS_URL}/laser?state={new_laser_state}"
        threading.Thread(target=send_command, args=(url,), daemon=True).start()
        laser_state = new_laser_state
        print(f"LASER: {laser_state.upper()}")


    # === DRAW CROSSHAIRS ===
    cv2.line(frame, (center_x, 0), (center_x, h), (0,255,0), 1)
    cv2.line(frame, (0, center_y), (w, center_y), (0,255,0), 1)
    cv2.rectangle(frame,
                  (center_x-FIRE_THRESHOLD_PX, center_y-FIRE_THRESHOLD_PX),
                  (center_x+FIRE_THRESHOLD_PX, center_y+FIRE_THRESHOLD_PX),
                  (0,255,255), 1)

    # === PROFILING ===
    frame_time = (time.time() - loop_start) * 1000
    frame_times.append(frame_time)
    
    # Last 200 frames only
    if len(frame_times) >= 3:
        recent = frame_times[-200:]
        min_t = min(recent)
        max_t = max(recent)
        avg_t = sum(recent) / len(recent)
        fps = 1000.0 / avg_t if avg_t > 0 else 0
    else:
        min_t = max_t = avg_t = frame_time
        fps = 0

    # ✅ DRAW REAL-TIME OVERLAY
    draw_stats_overlay(frame, fps, frame_time, min_t, avg_t, max_t, send_ok, send_fail)
    cv2.imshow("Iron Beam Brain (Hand Tracker)", frame)

    # === KEY INPUT ===
    key = cv2.waitKey(1) & 0xFF
    # ✅ Press L to print detailed report to terminal
    if key in (ord('l'), ord('L')):
        if len(frame_times) > 0:
            min_all = min(frame_times)
            max_all = max(frame_times)
            avg_all = sum(frame_times)/len(frame_times)
            std_all = statistics.pstdev(frame_times)
            fps_all = 1000.0 / avg_all if avg_all else 0

            print("\n\nLAPTOP (BRAIN) PERFORMANCE REPORT")
            print("--- Iron Beam Hand Tracking Stats ---")
            print(f"{len(frame_times)} frames processed")
            print(f"Frame time min/avg/max/stddev = "
                  f"{min_all:.2f}/{avg_all:.2f}/{max_all:.2f}/{std_all:.2f} ms")
            print(f"Approx FPS = {fps_all:.2f}")
            print("\nCommand Stats:")
            print(f"{send_total} sent, {send_ok} ok, {send_fail} failed")
            loss = (send_fail/send_total*100) if send_total else 0
            print(f"{loss:.2f}% packet loss")
            print("--------------------------------------------------------\n")

    if key == ord('q'):
        print("Quitting...")
        break

# --- CLEANUP ---
# cap.release()
# cv2.destroyAllWindows()
# hands.close()
print("Turning laser off.")
url = f"{HANDS_URL}/laser?state=off"
threading.Thread(target=send_command, args=(url,), daemon=True).start()
# time.sleep(20)

# keep streaming video

