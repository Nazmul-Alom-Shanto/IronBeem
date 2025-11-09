import cv2
import mediapipe as mp
import requests
import time
import numpy as np



# --- 1. CONSTANTS (USER MUST EDIT THESE) ---

# Get this from the ESP32-CAM Serial Monitor
# IMPORTANT: Use the :81/stream URL, NOT the main IP
EYE_STREAM_URL = "http://192.168.43.86:81/stream" # <-- !!! EDIT THIS (Your ESP32-CAM IP) !!!

# Get this from the NodeMCU/ESP32 Serial Monitor
HANDS_URL = "http://192.168.43.212" # <-- !!! EDIT THIS (Your ESP32 "Hands" IP) !!!

# --- 2. TUNING PARAMETERS ---

# How close (in pixels) the target needs to be to the center before firing
FIRE_THRESHOLD_PX = 20

# How long the target must be in the crosshairs before firing (in seconds)
FIRE_TIME_SECONDS = 1.0

# --- 3. STATE VARIABLES (Don't touch) ---
laser_state = "off"
on_target_since = None
# Start with a default guess, this will be updated automatically by the frame
center_x = 320 // 2
center_y = 240 // 2


# --- Load the ArUco dictionary (4x4_50) ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()

# --- 4. INITIALIZATION ---
print("Initializing 'Iron Beam Brain'...")

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,              # We only care about one hand
    min_detection_confidence=0.7, # Higher confidence for initial detection
    min_tracking_confidence=0.5   # Lower confidence for tracking (once detected)
)
mp_draw = mp.solutions.drawing_utils

# Connect to the ESP32-CAM video stream
print(f"Connecting to 'Eye' at {EYE_STREAM_URL}...")
cap = cv2.VideoCapture(EYE_STREAM_URL)

# Check if connection is successful
if not cap.isOpened():
    print("="*50)
    print("FATAL ERROR: Could not open video stream.")
    print(f"1. Check that EYE_STREAM_URL is correct: {EYE_STREAM_URL}")
    print("2. Ensure the ESP32-CAM is on and connected to Wi-Fi.")
    print("3. Ensure your laptop is on the same Wi-Fi network.")
    print("="*50)
    exit()

print("Connection to 'Eye' successful.")


# --- 5. HELPER FUNCTION ---
def send_command(url):
    """
    Sends an HTTP GET request to the "Hands" (ESP32).
    Uses a short timeout to prevent the main loop from hanging
    if the ESP32 is slow to respond.
    """
    try:
        # We don't need to wait for a response, so timeout is very short.
        requests.get(url, timeout=0.1)
    except requests.exceptions.RequestException as e:
        # This will catch timeouts, connection errors, etc.
        # We just print a warning and continue, so the program doesn't crash.
        print(f"COMMAND FAILED: {url} (Check 'Hands' connection)")


# --- 6. MAIN LOOP ---
print("Starting main loop. Press 'q' in the 'Iron Beam Brain' window to quit.")
while True:
    # --- 6.1. Get Frame from "Eye" ---
    success, frame = cap.read()
    if not success:
        print("Dropped frame from 'Eye'. Attempting to reconnect...")
        # Attempt to reconnect if the stream fails
        cap.release()
        cap = cv2.VideoCapture(EYE_STREAM_URL)
        time.sleep(1)
        continue

    # --- 6.2. Get Frame Dimensions ---
    # Update the center coordinates dynamically from the frame
    h, w, _ = frame.shape
    center_x = w // 2
    center_y = h // 2

    # --- 6.3. Process Frame with MediaPipe ---
    # Convert BGR (OpenCV) to RGB (MediaPipe)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Process the frame to find hands
    results = hands.process(frame_rgb)

    # --- 6.4. Find Target ---
    target_found = False
    error_x = 0
    error_y = 0

    if results.multi_hand_landmarks:
        target_found = True
        
        # Get the first (and only) hand
        hand_landmarks = results.multi_hand_landmarks[0]
        
        # As requested: Target Landmark 10 (MIDDLE_FINGER_PIP)
        # (This is the joint at the middle of the middle finger)
        target_point = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
        
        # Convert normalized (0.0-1.0) coordinates to pixel coordinates
        target_x = int(target_point.x * w)
        target_y = int(target_point.y * h)

        # --- 6.5. Calculate Aiming Error ---
        # Positive error means target is to the right/bottom
        # Negative error means target is to the left/top
        error_x = target_x - center_x
        error_y = target_y - center_y

        # --- 6.6. Draw on Frame (for the demo window) ---
        # Draw the full hand skeleton
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        # Draw a big red circle on the specific target point
        cv2.circle(frame, (target_x, target_y), 15, (0, 0, 255), -1)

    # --- 6.7. Send Aiming Command ---
    # Send aiming data to the "Hands" (ESP32) every frame
    if target_found:
        print("terget found")
        send_command(f"{HANDS_URL}/aim?x={error_x}&y={error_y}")

    # --- 6.8. Make Firing Decision ---
    is_on_target = target_found and abs(error_x) < FIRE_THRESHOLD_PX and abs(error_y) < FIRE_THRESHOLD_PX
    new_laser_state = "off" # Default to off

    if is_on_target:
        # Target is in the crosshairs
        if on_target_since is None:
            # We just acquired the target, start the timer
            on_target_since = time.time()
        
        # Check if the lock has been held long enough
        if (time.time() - on_target_since) > FIRE_TIME_SECONDS:
            new_laser_state = "on"
    else:
        # Target is lost or out of the crosshairs
        on_target_since = None # Reset the timer
        new_laser_state = "off"

    # --- 6.9. Send Firing Command (Only if the state changes) ---
    if new_laser_state != laser_state:
        # Send the command ONLY when the state flips (e.g., from "off" to "on")
        # This prevents flooding the ESP32 with "laser=on" commands
        send_command(f"{HANDS_URL}/laser?state={new_laser_state}")
        laser_state = new_laser_state # Update our current state
        print(f"LASER: {laser_state.upper()}")

    # --- 6.10. Show Demo Window ---
    # Draw the central crosshairs
    cv2.line(frame, (center_x, 0), (center_x, h), (0, 255, 0), 1) # Vertical line
    cv2.line(frame, (0, center_y), (w, center_y), (0, 255, 0), 1) # Horizontal line
    
    # Draw the firing threshold "box"
    cv2.rectangle(frame,
                  (center_x - FIRE_THRESHOLD_PX, center_y - FIRE_THRESHOLD_PX),
                  (center_x + FIRE_THRESHOLD_PX, center_y + FIRE_THRESHOLD_PX),
                  (0, 255, 255), 1) # Yellow box

    # Display the final image
    cv2.imshow("Iron Beam Brain", frame)

    # --- 6.11. Quit Condition ---
    # Wait for 1ms, and check if the 'q' key was pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("'q' pressed. Shutting down...")
        break

# --- 7. CLEANUP ---
print("Cleaning up...")
cap.release()
cv2.destroyAllWindows()
# Send one final command to ensure the laser is OFF
send_command(f"{HANDS_URL}/laser?state=off")
print("Script terminated. Laser OFF.")