"""WebSocket connection manager with auto-reconnection."""

import time
import websocket


class WebSocketManager:
    """Manages WebSocket connection with automatic reconnection."""
    
    def __init__(self, url: str):
        """
        Initialize WebSocket manager.
        
        Args:
            url: WebSocket URL (e.g., "ws://10.42.0.164:81")
        """
        self.url = url
        self.ws = None
    
    def connect(self) -> bool:
        """
        Establish WebSocket connection.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            print(f"Connecting to WebSocket at {self.url}...")
            self.ws = websocket.create_connection(self.url)
            print("✅ WebSocket connected.")
            return True
        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False
    
    def send(self, message: str) -> bool:
        """
        Send message with automatic reconnection on failure.
        
        Args:
            message: String message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if self.ws is None:
                print("WebSocket not connected. Attempting to connect...")
                if not self.connect():
                    return False
            
            self.ws.send(message)
            return True
            
        except Exception as e:
            print(f"WS send error: {e}. Reconnecting...")
            try:
                self._reconnect()
                self.ws.send(message)  # Retry send
                print("Reconnected and sent.")
                return True
            except Exception as e2:
                print(f"Reconnect failed: {e2}")
                time.sleep(1)
                return False
    
    def _reconnect(self):
        """Internal reconnection logic."""
        try:
            if self.ws:
                self.ws.close()
        except:
            pass
        
        self.ws = websocket.create_connection(self.url)
    
    def close(self):
        """Close WebSocket connection."""
        if self.ws:
            try:
                self.ws.close()
                print("WebSocket closed.")
            except Exception as e:
                print(f"Error closing WebSocket: {e}")
