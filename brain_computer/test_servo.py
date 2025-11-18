import websocket
import time

# --- 1. CONSTANTS ---
# ✅ ONE URL for all commands
HANDS_WS_URL = "ws://10.42.0.164:81"

# --- 2. CONNECT ---
print(f"Attempting to connect to {HANDS_WS_URL}...")
ws = websocket.WebSocket()
try:
    ws.connect(HANDS_WS_URL, timeout=5)
    print("✅ Successfully connected!")
    print("---")
    print("Enter command to send. Examples:")
    print("  '90,90'   (to center servos)")
    print("  '0,0'     (to test min range)")
    print("  '180,180' (to test max range)")
    print("  'laser_on'")
    print("  'laser_off'")
    print("  'q' or 'exit' (to quit)")
    print("---")

    while True:
        try:
            cmd = input("Enter command > ")
            
            if cmd.lower() == 'q' or cmd.lower() == 'exit':
                print("Disconnecting...")
                break
            
            # Don't send empty strings
            if not cmd:
                continue

            # Send the command
            ws.send(cmd)
            print(f"Sent: '{cmd}'")

        except (websocket.WebSocketConnectionClosedException, BrokenPipeError):
            print("❌ Connection lost. Attempting to reconnect...")
            try:
                ws.connect(HANDS_WS_URL, timeout=5)
                print("✅ Reconnected!")
            except Exception as e:
                print(f"Reconnect failed: {e}")
                time.sleep(2)
        except KeyboardInterrupt:
            print("\nUser interrupted. Exiting.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

except Exception as e:
    print(f"❌ Failed to connect: {e}")
    print("Check the URL and ensure the ESP32 is running and on the network.")

finally:
    if ws.connected:
        ws.close()
    print("Connection closed. Goodbye.")