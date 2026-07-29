"""Base detector interface for all target detection implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np


@dataclass
class DetectionResult:
    """Result of a target detection operation."""
    
    target_x: int
    target_y: int
    confidence: float = 1.0
    
    def get_error(self, center_x: int, center_y: int) -> tuple[int, int]:
        """
        Calculate error from center.
        
        Args:
            center_x: Frame center X coordinate
            center_y: Frame center Y coordinate
            
        Returns:
            (error_x, error_y) tuple
        """
        return self.target_x - center_x, self.target_y - center_y


class BaseDetector(ABC):
    """Abstract base class for all target detectors."""
    
    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult | None:
        """
        Detect target in frame.
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            DetectionResult if target found, None otherwise
        """
        pass
    
    @abstractmethod
    def draw_overlay(self, frame: np.ndarray, result: DetectionResult | None):
        """
        Draw detection overlay on frame (in-place modification).
        
        Args:
            frame: BGR image to draw on
            result: Detection result (or None if no target)
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get detector name for display.
        
        Returns:
            Human-readable detector name
        """
        pass
    
    def cleanup(self):
        """
        Cleanup resources (optional override).
        Called when detector is no longer needed.
        """
        pass
