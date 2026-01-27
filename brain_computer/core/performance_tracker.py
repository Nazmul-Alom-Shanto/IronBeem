"""Performance tracking module for FPS and frame time statistics."""

from collections import deque


class PerformanceTracker:
    """Tracks frame times and calculates performance statistics."""
    
    def __init__(self, history_size: int = 200):
        """
        Initialize performance tracker.
        
        Args:
            history_size: Number of frames to keep in history
        """
        self.frame_times = deque(maxlen=history_size)
    
    def record_frame(self, frame_time_ms: float):
        """
        Record a frame time.
        
        Args:
            frame_time_ms: Frame processing time in milliseconds
        """
        self.frame_times.append(frame_time_ms)
    
    def get_stats(self) -> dict:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with keys: fps, frame_time, min_time, avg_time, max_time
            Returns zeros if insufficient data.
        """
        if len(self.frame_times) < 3:
            return {
                'fps': 0.0,
                'frame_time': self.frame_times[-1] if self.frame_times else 0.0,
                'min_time': 0.0,
                'avg_time': 0.0,
                'max_time': 0.0
            }
        
        min_time = min(self.frame_times)
        max_time = max(self.frame_times)
        avg_time = sum(self.frame_times) / len(self.frame_times)
        fps = 1000.0 / avg_time if avg_time > 0 else 0.0
        
        return {
            'fps': fps,
            'frame_time': self.frame_times[-1],
            'min_time': min_time,
            'avg_time': avg_time,
            'max_time': max_time
        }
