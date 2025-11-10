import cv2
import cv2.aruco as aruco
import requests
import time
import numpy as np
import threading  # ««« ADDED: Import the threading library

# --- 1. CONSTANTS (USER MUST EDIT THESE) ---
EYE_STREAM_URL = "http://192.168.43.86/stream"  # ESP32-CAM MJPEG stream URL
HANDS_URL = "http://192.168.43.212"               # ESP32 "Hands" IP

# --- 2. TUNING PARAMETERS ---
FIRE_THRESHOLD_PX = 45
FIRE_TIME_SECONDS = 0.0

# --- 3. STATE VARIABLES ---
laser_state = "off"
on_target_since = None
center_x = 640 // 2
center_y = 480 // 2

# --- 4. ArUco Setup ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)
TARGET_ID = 0  # Only track marker ID 0

# --- 5. Helper function ---
def send_command(url):
    """
    This function now runs in a separate thread.
    It no longer prints, to avoid flooding the console.
    """
    try:
        requests.get(url, timeout=0.5)
    except requests.exceptions.RequestException:
        pass  # ««« CHANGED: Silently fail to avoid console spam

# --- 6. Initialize Stream ---
cap = cv2.VideoCapture(EYE_STREAM_URL)
if not cap.isOpened():
    print("❌ Could not open video stream.")
    exit()
print("✅ Stream opened.")

# --- 7. Main Loop ---
while True:
    success, frame = cap.read()
    if not success:
        print("Dropped frame. Reconnecting...")
        cap.release()
        time.sleep(0.5)
        cap = cv2.VideoCapture(EYE_STREAM_URL)
        continue

    h, w, _ = frame.shape
    center_x, center_y = w // 2, h // 2

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)

    target_found = False
    error_x = 0
    error_y = 0

    if ids is not None:
        for i, corner in zip(ids.flatten(), corners):
            if i == TARGET_ID:
                target_found = True
                c = corner[0].astype(int)
                # Center of marker
                target_x, target_y = int(np.mean(c[:, 0])), int(np.mean(c[:, 1]))
                error_x = target_x - center_x
                error_y = target_y - center_y

                # Draw marker
                aruco.drawDetectedMarkers(frame, [corner], np.array([[i]]))
                # Draw target center
                cv2.circle(frame, (target_x, target_y), 10, (0, 0, 255), -1)
                
                # ««« REMOVED: Print statement here to reduce spam.
                # You can add it back if you need to debug.
                # print(f"Error (x, y): {error_x}, {error_y}") 
                break

    # Send aiming command
    if target_found:
        # ««« CHANGED: This now runs in a separate thread
        # This is the "fire and forget" non-blocking call.
        url = f"{HANDS_URL}/aim?x={error_x}&y={error_y}"
        threading.Thread(target=send_command, args=(url,), daemon=True).start()

    # Fire logic
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
        # ««« CHANGED: This also runs in a separate thread
        url = f"{HANDS_URL}/laser?state={new_laser_state}"
        threading.Thread(target=send_command, args=(url,), daemon=True).start()
        
        laser_state = new_laser_state
        print(f"LASER: {laser_state.upper()}")

    # Draw crosshairs
    cv2.line(frame, (center_x, 0), (center_x, h), (0, 255, 0), 1)
    cv2.line(frame, (0, center_y), (w, center_y), (0, 255, 0), 1)
    cv2.rectangle(frame,
                  (center_x - FIRE_THRESHOLD_PX, center_y - FIRE_THRESHOLD_PX),
                  (center_x + FIRE_THRESHOLD_PX, center_y + FIRE_THRESHOLD_PX),
                  (0, 255, 255), 1)

    cv2.imshow("Iron Beam Brain", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Quitting...")
        break

cap.release()
cv2.destroyAllWindows()

# Send final "laser off" command in a thread
print("Turning laser off.")
url = f"{HANDS_URL}/laser?state=off"
threading.Thread(target=send_command, args=(url,), daemon=True).start() # ««« CHANGED
time.sleep(0.5) # ««« ADDED: Give the final command a moment to send