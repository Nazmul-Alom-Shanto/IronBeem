"""Configuration constants for IronBeem tracking system."""

# === NETWORK CONFIGURATION ===
EYE_STREAM_URL = "http://10.42.0.176/stream"
HANDS_WS_URL = "ws://10.42.0.164:81"

# === SERVO CONFIGURATION ===
PAN_GAIN = 0.02
TILT_GAIN = -0.021

PAN_MIN = 5
PAN_MAX = 175
TILT_MIN = 20
TILT_MAX = 100

INITIAL_PAN = 90.0
INITIAL_TILT = 60.0

# === LASER CONFIGURATION ===
FIRE_THRESHOLD_PX = 40
FIRE_TIME_SECONDS = 0.0  # Time target must be held before firing

# === DISPLAY CONFIGURATION ===
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720

# Center offsets for different detectors
CENTER_OFFSET_ARUCO = (-15, 25)     # (x, y) offset for ArUco
CENTER_OFFSET_MEDIAPIPE = (0, 0)    # (x, y) offset for MediaPipe

# === DETECTOR CONFIGURATION ===
# ArUco settings
ARUCO_TARGET_ID = 0

# MediaPipe settings
MEDIAPIPE_MAX_HANDS = 1
MEDIAPIPE_MIN_DETECTION_CONFIDENCE = 0.5
MEDIAPIPE_MIN_TRACKING_CONFIDENCE = 0.25

# === PERFORMANCE CONFIGURATION ===
PERFORMANCE_HISTORY_SIZE = 200  # Number of frames to track for FPS calculation
