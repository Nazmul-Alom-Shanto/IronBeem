"""ArUco marker detector implementation."""

import cv2
import cv2.aruco as aruco
import numpy as np
from .base_detector import BaseDetector, DetectionResult


class ArucoDetector(BaseDetector):
    """Detects ArUco markers for target tracking."""
    
    def __init__(self, target_id: int = 0, dict_type=aruco.DICT_4X4_50):
        """
        Initialize ArUco detector.
        
        Args:
            target_id: ID of the marker to track
            dict_type: ArUco dictionary type
        """
        self.target_id = target_id
        
        # Setup ArUco detector
        aruco_dict = aruco.getPredefinedDictionary(dict_type)
        parameters = aruco.DetectorParameters()
        self.detector = aruco.ArucoDetector(aruco_dict, parameters)
    
    def detect(self, frame: np.ndarray) -> DetectionResult | None:
        """
        Detect ArUco marker in frame.
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            DetectionResult with marker center, or None if not found
        """
        # Convert to grayscale (ArUco requires grayscale)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect markers
        corners, ids, _ = self.detector.detectMarkers(gray)
        
        # Find target marker
        if ids is not None:
            # Use numpy to find target directly
            target_idx = np.where(ids.flatten() == self.target_id)[0]
            if len(target_idx) > 0:
                idx = target_idx[0]
                corner = corners[idx][0].astype(int)
                
                # Calculate center of marker
                target_x = int(np.mean(corner[:, 0]))
                target_y = int(np.mean(corner[:, 1]))
                
                return DetectionResult(target_x, target_y, confidence=1.0)
        
        return None
    
    def draw_overlay(self, frame: np.ndarray, result: DetectionResult | None):
        """
        Draw ArUco marker overlay.
        
        Args:
            frame: BGR image to draw on
            result: Detection result
        """
        if result is None:
            return
        
        # Draw target circle
        cv2.circle(frame, (result.target_x, result.target_y), 10, (0, 0, 255), -1)
        
        # Optionally re-detect to draw full marker outline
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        
        if ids is not None:
            for i, corner in zip(ids.flatten(), corners):
                if i == self.target_id:
                    aruco.drawDetectedMarkers(frame, [corner], np.array([[i]]))
                    break
    
    def get_name(self) -> str:
        """Get detector name."""
        return f"ArUco (ID={self.target_id})"
