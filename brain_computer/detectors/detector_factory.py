"""Factory for creating detector instances."""

from .base_detector import BaseDetector
from .aruco_detector import ArucoDetector
from .mediapipe_detector import MediaPipeDetector


def create_detector(detector_type: str, **kwargs) -> BaseDetector:
    """
    Create a detector instance by type.
    
    Args:
        detector_type: Type of detector ("aruco" or "mediapipe")
        **kwargs: Additional arguments passed to detector constructor
        
    Returns:
        Detector instance
        
    Raises:
        ValueError: If detector_type is unknown
        
    Examples:
        >>> detector = create_detector("aruco", target_id=0)
        >>> detector = create_detector("mediapipe")
    """
    detector_type = detector_type.lower()
    
    if detector_type == "aruco":
        return ArucoDetector(**kwargs)
    elif detector_type == "mediapipe":
        return MediaPipeDetector(**kwargs)
    else:
        raise ValueError(
            f"Unknown detector type: '{detector_type}'. "
            f"Valid options: 'aruco', 'mediapipe'"
        )


def list_available_detectors() -> list[str]:
    """
    Get list of available detector types.
    
    Returns:
        List of detector type strings
    """
    return ["aruco", "mediapipe"]
