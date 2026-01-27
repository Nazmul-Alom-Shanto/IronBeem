"""Servo control module for pan/tilt tracking."""


class ServoController:
    """Controls servo pan/tilt movements with proportional gains and safety limits."""
    
    def __init__(
        self,
        pan_gain: float = 0.02,
        tilt_gain: float = -0.021,
        pan_limits: tuple[int, int] = (5, 175),
        tilt_limits: tuple[int, int] = (20, 100),
        initial_pan: float = 90.0,
        initial_tilt: float = 60.0
    ):
        """
        Initialize servo controller.
        
        Args:
            pan_gain: Proportional gain for pan axis (positive = left on error)
            tilt_gain: Proportional gain for tilt axis (negative inverts direction)
            pan_limits: (min, max) angle limits for pan servo
            tilt_limits: (min, max) angle limits for tilt servo
            initial_pan: Starting pan angle
            initial_tilt: Starting tilt angle
        """
        self.pan_gain = pan_gain
        self.tilt_gain = tilt_gain
        self.pan_min, self.pan_max = pan_limits
        self.tilt_min, self.tilt_max = tilt_limits
        
        # Current state
        self.current_pan = initial_pan
        self.current_tilt = initial_tilt
        
        # ✅ Track last sent position to avoid redundant commands
        self.last_sent_pan = None
        self.last_sent_tilt = None
    
    def reset(self, pan: float = 90.0, tilt: float = 60.0) -> tuple[int, int]:
        """
        Reset servos to specified position.
        
        Args:
            pan: Pan angle to reset to
            tilt: Tilt angle to reset to
            
        Returns:
            (pan_int, tilt_int) command tuple
        """
        self.current_pan = max(self.pan_min, min(self.pan_max, pan))
        self.current_tilt = max(self.tilt_min, min(self.tilt_max, tilt))
        
        # Reset tracking (force send on next command)
        self.last_sent_pan = None
        self.last_sent_tilt = None
        
        return int(round(self.current_pan)), int(round(self.current_tilt))
    
    def calculate_movement(self, error_x: int, error_y: int) -> tuple[int, int]:
        """
        Calculate servo movement based on target error.
        
        Args:
            error_x: Horizontal pixel error (target_x - center_x)
            error_y: Vertical pixel error (target_y - center_y)
            
        Returns:
            (pan_int, tilt_int) command tuple
        """
        # Calculate target angles
        new_pan = self.current_pan - (error_x * self.pan_gain)
        new_tilt = self.current_tilt - (error_y * self.tilt_gain)
        
        # Clamp to safety limits (prevents integrator wind-up)
        self.current_pan = max(self.pan_min, min(self.pan_max, new_pan))
        self.current_tilt = max(self.tilt_min, min(self.tilt_max, new_tilt))
        
        # Round to integers for sending
        pan_int = int(round(self.current_pan))
        tilt_int = int(round(self.current_tilt))
        
        return pan_int, tilt_int
    
    def get_current_angles(self) -> tuple[float, float]:
        """
        Get current servo angles.
        
        Returns:
            (pan, tilt) angle tuple
        """
        return self.current_pan, self.current_tilt
    
    def has_changed(self) -> bool:
        """
        Check if position has changed since last send.
        
        Returns:
            True if position changed, False otherwise
        """
        pan_int = int(round(self.current_pan))
        tilt_int = int(round(self.current_tilt))
        
        return (pan_int != self.last_sent_pan or 
                tilt_int != self.last_sent_tilt or
                self.last_sent_pan is None)
    
    def update_last_sent(self):
        """Update the last sent position to current position."""
        self.last_sent_pan = int(round(self.current_pan))
        self.last_sent_tilt = int(round(self.current_tilt))
