import cv2
import cv2.aruco as aruco
import requests
import time
import numpy as np
import threading
import statistics

# --- 1. CONSTANTS ---
EYE_STREAM_URL = "http://10.42.0.176/stream"
HANDS_URL = "http://10.42.0.164:81"

# --- 2. TUNING PARAMETERS ---
FIRE_THRESHOLD_PX = 45
FIRE_TIME_SECONDS = 0.0

# --- 3. STATE VARIABLES ---
laser_state = "off"
on_target_since = None
center_x = 640 // 2
center_y = 480 // 2

# --- PERFORMANCE PROFILE ---
frame_times = []
send_ok = 0
send_fail = 0
send_total = 0


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


# --- 4. ArUco Setup ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)
TARGET_ID = 0


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


# --- 6. Initialize Stream ---
cap = cv2.VideoCapture(EYE_STREAM_URL)
if not cap.isOpened():
    print("❌ Could not open video stream.")
    exit()
print("✅ Stream opened.")


# --- 7. MAIN LOOP ---
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
    center_x, center_y = w // 2, h // 2

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

    # === SEND AIM COMMAND ===
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

        # url = f"{HANDS_URL}/aim?x={error_x}&y={error_y}"
        # threading.Thread(target=send_command, args=(url,), daemon=True).start()

    # === LASER FIRING LOGIC ===
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

    if len(frame_times) >= 3:
        recent = frame_times[-200:]
        min_t = min(recent)
        max_t = max(recent)
        avg_t = sum(recent) / len(recent)
        fps = 1000.0 / avg_t if avg_t else 0
    else:
        min_t = max_t = avg_t = frame_time
        fps = 0

    # ✅ DRAW OVERLAY
    draw_stats_overlay(frame, fps, frame_time, min_t, avg_t, max_t, send_ok, send_fail)

    cv2.imshow("Iron Beam Brain (ArUco Tracker)", frame)

    key = cv2.waitKey(1) & 0xFF

    # ✅ TERMINAL REPORT (LIKE PING)
    if key in (ord('l'), ord('L')):
        if len(frame_times) > 0:
            min_all = min(frame_times)
            max_all = max(frame_times)
            avg_all = sum(frame_times)/len(frame_times)
            std_all = statistics.pstdev(frame_times)
            fps_all = 1000.0 / avg_all if avg_all else 0

            print("\n\nLAPTOP (BRAIN) PERFORMANCE REPORT")
            print("--- Iron Beam ArUco Tracking Stats ---")
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
cap.release()
cv2.destroyAllWindows()

print("Turning laser off...")
url = f"{HANDS_URL}/laser?state=off"
threading.Thread(target=send_command, args=(url,), daemon=True).start()
time.sleep(0.5)

