#!/usr/bin/env python3
"""
IronBeem Brain - Modular Target Tracking System

Usage:
    python main.py --detector aruco
    python main.py --detector mediapipe --no-display
"""

import cv2
import time
import argparse
import sys

# Local imports
from core import ServoController, LaserController, WebSocketManager, PerformanceTracker
from detectors import create_detector, list_available_detectors
import config


def draw_stats_overlay(frame, stats, servo_angles):
    """Draw performance statistics overlay."""
    y = 22
    step = 22
    
    cv2.putText(frame, f"FPS: {stats['fps']:.1f}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    y += step
    
    cv2.putText(frame, f"Frame: {stats['frame_time']:.1f} ms", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    y += step
    
    cv2.putText(frame, 
                f"Min/Avg/Max: {stats['min_time']:.1f}/{stats['avg_time']:.1f}/{stats['max_time']:.1f} ms",
                (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
    y += step
    
    pan, tilt = servo_angles
    cv2.putText(frame, f"Pan/Tilt: {pan:.1f}/{tilt:.1f}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)


def draw_crosshair(frame, center_x, center_y, fire_threshold):
    """Draw targeting crosshair and fire zone."""
    h, w, _ = frame.shape
    
    # Crosshair lines
    cv2.line(frame, (center_x, 0), (center_x, h), (0, 255, 0), 1)
    cv2.line(frame, (0, center_y), (w, center_y), (0, 255, 0), 1)
    
    # Fire threshold box
    cv2.rectangle(frame,
                  (center_x - fire_threshold, center_y - fire_threshold),
                  (center_x + fire_threshold, center_y + fire_threshold),
                  (0, 255, 255), 1)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="IronBeem Brain - Modular Target Tracking System"
    )
    
    parser.add_argument(
        "--detector",
        type=str,
        default="aruco",
        choices=list_available_detectors(),
        help=f"Detector type (choices: {', '.join(list_available_detectors())})"
    )
    
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable GUI display (headless mode)"
    )
    
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Enable benchmark mode (print performance stats)"
    )
    
    return parser.parse_args()


def main():
    """Main orchestrator."""
    # Parse arguments
    args = parse_args()
    
    print("=" * 60)
    print("IronBeem Brain - Modular Target Tracking System".center(60))
    print("=" * 60)
    print(f"Detector: {args.detector}")
    print(f"Display: {'disabled' if args.no_display else 'enabled'}")
    print("=" * 60)
    
    # === INITIALIZATION ===
    
    # Create detector
    try:
        print(f"\n[1/5] Initializing {args.detector} detector...")
        if args.detector == "aruco":
            detector = create_detector("aruco", target_id=config.ARUCO_TARGET_ID)
            center_offset = config.CENTER_OFFSET_ARUCO
        elif args.detector == "mediapipe":
            detector = create_detector(
                "mediapipe",
                max_num_hands=config.MEDIAPIPE_MAX_HANDS,
                min_detection_confidence=config.MEDIAPIPE_MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MEDIAPIPE_MIN_TRACKING_CONFIDENCE
            )
            center_offset = config.CENTER_OFFSET_MEDIAPIPE
        print(f"✅ {detector.get_name()} initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize detector: {e}")
        sys.exit(1)
    
    # Create controllers
    print("\n[2/5] Initializing controllers...")
    servo = ServoController(
        pan_gain=config.PAN_GAIN,
        tilt_gain=config.TILT_GAIN,
        pan_limits=(config.PAN_MIN, config.PAN_MAX),
        tilt_limits=(config.TILT_MIN, config.TILT_MAX),
        initial_pan=config.INITIAL_PAN,
        initial_tilt=config.INITIAL_TILT
    )
    
    laser = LaserController(
        fire_threshold_px=config.FIRE_THRESHOLD_PX,
        fire_delay_seconds=config.FIRE_TIME_SECONDS
    )
    
    perf = PerformanceTracker(history_size=config.PERFORMANCE_HISTORY_SIZE)
    print("✅ Controllers initialized.")
    
    # Connect to WebSocket
    print("\n[3/5] Connecting to WebSocket...")
    ws = WebSocketManager(config.HANDS_WS_URL)
    if not ws.connect():
        print("❌ Failed to connect to WebSocket.")
        sys.exit(1)
    
    # Reset servos
    print("[4/5] Resetting servo position...")
    reset_pan, reset_tilt = servo.reset()
    ws.send(f"{reset_pan},{reset_tilt}")
    print(f"✅ Servos reset to ({reset_pan}, {reset_tilt}).")
    
    # Open video stream
    print(f"\n[5/5] Opening video stream from {config.EYE_STREAM_URL}...")
    cap = cv2.VideoCapture(config.EYE_STREAM_URL)
    if not cap.isOpened():
        print("❌ Could not open video stream.")
        ws.close()
        sys.exit(1)
    print("✅ Video stream opened.")
    
    # Setup display window
    if not args.no_display:
        window_name = f"IronBeem - {detector.get_name()}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
    
    print("\n" + "=" * 60)
    print("SYSTEM READY - Press 'q' to quit".center(60))
    print("=" * 60 + "\n")
    
    # === MAIN LOOP ===
    try:
        while True:
            loop_start = time.time()
            
            # Capture frame
            success, frame = cap.read()
            if not success:
                print("Dropped frame. Reconnecting...")
                cap.release()
                time.sleep(0.5)
                cap = cv2.VideoCapture(config.EYE_STREAM_URL)
                continue
            
            # Calculate frame center with offset
            h, w, _ = frame.shape
            center_x = w // 2 + center_offset[0]
            center_y = h // 2 + center_offset[1]
            
            # === DETECTION ===
            result = detector.detect(frame)
            
            # === CONTROL ===
            if result:
                # Calculate error
                error_x, error_y = result.get_error(center_x, center_y)
                
                # Update servo position
                pan_int, tilt_int = servo.calculate_movement(error_x, error_y)
                
                # ✅ Only send command if position actually changed
                if servo.has_changed():
                    ws.send(f"{pan_int},{tilt_int}")
                    servo.update_last_sent()
                
                # Update laser state
                laser_cmd = laser.update(True, error_x, error_y)
                if laser_cmd:
                    ws.send(laser_cmd)
                    if args.benchmark:
                        print(f"LASER: {laser_cmd}")
            else:
                # No target - turn off laser
                laser_cmd = laser.update(False, 0, 0)
                if laser_cmd:
                    ws.send(laser_cmd)
                    if args.benchmark:
                        print(f"LASER: {laser_cmd}")
            
            # === DISPLAY ===
            if not args.no_display:
                # Draw detection overlay
                detector.draw_overlay(frame, result)
                
                # Draw crosshair
                draw_crosshair(frame, center_x, center_y, laser.get_threshold_px())
                
                # Draw stats
                stats = perf.get_stats()
                servo_angles = servo.get_current_angles()
                draw_stats_overlay(frame, stats, servo_angles)
                
                # Show frame
                cv2.imshow(window_name, frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nQuitting...")
                    break
            
            # === PERFORMANCE TRACKING ===
            frame_time = (time.time() - loop_start) * 1000
            perf.record_frame(frame_time)
            
            # Print benchmark stats
            if args.benchmark and int(time.time() * 10) % 10 == 0:  # Every 1 second
                stats = perf.get_stats()
                print(f"FPS: {stats['fps']:.1f} | "
                      f"Avg: {stats['avg_time']:.1f}ms | "
                      f"Min: {stats['min_time']:.1f}ms | "
                      f"Max: {stats['max_time']:.1f}ms")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    
    finally:
        # === CLEANUP ===
        print("\nCleaning up resources...")
        
        # Turn off laser
        print("Turning laser off...")
        ws.send(laser.force_off())
        
        # Close connections
        ws.close()
        cap.release()
        
        if not args.no_display:
            cv2.destroyAllWindows()
        
        # Cleanup detector
        detector.cleanup()
        
        time.sleep(0.5)
        print("Exiting.\n")


if __name__ == "__main__":
    main()