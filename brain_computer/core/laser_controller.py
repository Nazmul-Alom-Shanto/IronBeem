"""Laser control module for target engagement."""

import time


class LaserController:
    """Controls laser on/off based on target acquisition and hold time."""
    
    def __init__(
        self,
        fire_threshold_px: int = 40,
        fire_delay_seconds: float = 0.0
    ):
        """
        Initialize laser controller.
        
        Args:
            fire_threshold_px: Maximum error (in pixels) to consider "on target"
            fire_delay_seconds: Time target must be held before firing
        """
        self.fire_threshold = fire_threshold_px
        self.fire_delay = fire_delay_seconds
        
        # State tracking
        self.laser_state = "off"
        self.on_target_since = None
    
    def update(self, target_found: bool, error_x: int, error_y: int) -> str | None:
        """
        Update laser state based on target status.
        
        Args:
            target_found: Whether a target was detected
            error_x: Horizontal pixel error
            error_y: Vertical pixel error
            
        Returns:
            "laser_on", "laser_off", or None if no state change
        """
        is_on_target = (
            target_found and
            abs(error_x) < self.fire_threshold and
            abs(error_y) < self.fire_threshold
        )
        
        now = time.time()
        
        if is_on_target:
            # Target acquired - start timer if first frame
            if self.on_target_since is None:
                self.on_target_since = now
            
            # Check if hold time expired
            if (now - self.on_target_since) > self.fire_delay:
                if self.laser_state == "off":
                    self.laser_state = "on"
                    return "laser_on"
        else:
            # Target lost - reset timer
            self.on_target_since = None
            
            if self.laser_state == "on":
                self.laser_state = "off"
                return "laser_off"
        
        return None  # No state change
    
    def get_state(self) -> str:
        """Get current laser state."""
        return self.laser_state
    
    def force_off(self) -> str:
        """Force laser off (for cleanup)."""
        self.laser_state = "off"
        self.on_target_since = None
        return "laser_off"
    
    def get_threshold_px(self) -> int:
        """Get fire threshold for drawing overlay."""
        return self.fire_threshold
