import cv2
import cv2.aruco as aruco
import numpy as np

# --- Your ESP32-CAM stream URL ---
EYE_STREAM_URL = "http://192.168.43.86:81/stream"  # <-- Change this if needed

# --- Load the ArUco dictionary (4x4_50) ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()

# --- Initialize the video stream ---
cap = cv2.VideoCapture(EYE_STREAM_URL)

if not cap.isOpened():
    print("❌ Cannot open stream. Check the IP or camera connection.")
    exit()

print("✅ Stream opened successfully. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Failed to grab frame.")
        break

    # Convert to grayscale for detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect ArUco markers
    detector = aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, rejected = detector.detectMarkers(gray)

    # Draw detected markers
    if ids is not None:
        aruco.drawDetectedMarkers(frame, corners, ids)
        for i, corner in zip(ids, corners):
            c = corner[0].astype(int)
            cx, cy = int(np.mean(c[:, 0])), int(np.mean(c[:, 1]))
            cv2.putText(frame, f"ID: {int(i)}", (cx - 30, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("ArUco Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
