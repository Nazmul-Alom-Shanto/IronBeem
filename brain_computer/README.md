# IronBeem Brain - Modular Architecture

## Quick Start

### Run with ArUco detector:
```bash
python main.py --detector aruco
```

### Run with MediaPipe detector:
```bash
python main.py --detector mediapipe
```

### Headless mode (no display):
```bash
python main.py --detector aruco --no-display
```

### Benchmark mode:
```bash
python main.py --detector aruco --benchmark
```

## Architecture

```
brain_computer/
├── core/                       # Core control modules
│   ├── servo_controller.py    # Servo pan/tilt control
│   ├── laser_controller.py    # Laser on/off logic
│   ├── websocket_manager.py   # WebSocket connection
│   └── performance_tracker.py # FPS tracking
├── detectors/                  # Detection implementations
│   ├── base_detector.py        # Abstract base class
│   ├── aruco_detector.py       # ArUco markers
│   ├── mediapipe_detector.py   # Hand tracking
│   └── detector_factory.py     # Factory pattern
├── config.py                   # Configuration
├── main.py                     # Main orchestrator
└── archive/                    # Old implementations
    ├── follow_0.py
    ├── follow_0-new.py
    └── debug.py
```

## Adding New Detectors

1. Create a new file in `detectors/`:
```python
# detectors/color_detector.py
from .base_detector import BaseDetector, DetectionResult
import cv2
import numpy as np

class ColorDetector(BaseDetector):
    def detect(self, frame):
        # Your color detection logic
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_color, upper_color)
        # Find contours, get center...
        return DetectionResult(x, y)
    
    def draw_overlay(self, frame, result):
        # Draw visualization
        pass
    
    def get_name(self):
        return "Color Tracker"
```

2. Register in `detector_factory.py`:
```python
def create_detector(detector_type: str, **kwargs):
    if detector_type == "color":
        return ColorDetector(**kwargs)
    # ... existing detectors
```

3. Run it:
```bash
python main.py --detector color
```

## Configuration

Edit `config.py` to adjust:
- Network URLs
- Servo gains and limits
- Fire thresholds
- Detector parameters

## Dependencies

```bash
pip install opencv-python mediapipe websocket-client numpy
```
