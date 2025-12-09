"""
SIP Server Example
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server.sip_server import SIPServer


def on_incoming_call(call_id, from_uri, to_uri):
    """Callback for incoming calls."""
    print(f"Incoming call: {call_id}")
    print(f"  From: {from_uri}")
    print(f"  To: {to_uri}")


def main():
    """Run SIP server."""
    # Create server
    server = SIPServer(config_path="config/server_config.yaml")
    
    # Set callback for incoming calls
    server.set_on_incoming_call(on_incoming_call)
    
    # Start server
    print("Starting SIP server...")
    server.start()
    
    try:
        print("SIP server is running. Press Ctrl+C to stop.")
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.stop()
        print("Server stopped")


if __name__ == "__main__":
    main()

