"""MediaPipe hand tracking detector implementation."""

import cv2
import mediapipe as mp
import numpy as np
from .base_detector import BaseDetector, DetectionResult


class MediaPipeDetector(BaseDetector):
    """Detects hands using MediaPipe for target tracking."""
    
    def __init__(
        self,
        target_landmark=None,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.25
    ):
        """
        Initialize MediaPipe detector.
        
        Args:
            target_landmark: Landmark to track (default: MIDDLE_FINGER_MCP)
            max_num_hands: Maximum hands to detect
            min_detection_confidence: Detection confidence threshold
            min_tracking_confidence: Tracking confidence threshold
        """
        # Setup MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Target landmark
        if target_landmark is None:
            self.target_landmark = self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP
        else:
            self.target_landmark = target_landmark
        
        # Cache last result for drawing
        self._last_hand_landmarks = None
    
    def detect(self, frame: np.ndarray) -> DetectionResult | None:
        """
        Detect hand in frame.
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            DetectionResult with hand landmark position, or None if not found
        """
        # Convert to RGB (MediaPipe requires RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = self.hands.process(frame_rgb)
        
        # Extract target landmark
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            self._last_hand_landmarks = hand_landmarks  # Cache for drawing
            
            target_point = hand_landmarks.landmark[self.target_landmark]
            h, w, _ = frame.shape
            target_x = int(target_point.x * w)
            target_y = int(target_point.y * h)
            
            return DetectionResult(target_x, target_y, confidence=1.0)
        
        self._last_hand_landmarks = None
        return None
    
    def draw_overlay(self, frame: np.ndarray, result: DetectionResult | None):
        """
        Draw hand skeleton overlay.
        
        Args:
            frame: BGR image to draw on
            result: Detection result
        """
        if result is None or self._last_hand_landmarks is None:
            return
        
        # Draw hand skeleton
        self.mp_drawing.draw_landmarks(
            frame,
            self._last_hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS
        )
        
        # Draw target point
        cv2.circle(frame, (result.target_x, result.target_y), 10, (0, 0, 255), -1)
    
    def get_name(self) -> str:
        """Get detector name."""
        return "MediaPipe Hands"
    
    def cleanup(self):
        """Release MediaPipe resources."""
        if self.hands:
            self.hands.close()
