"""
Basic Call Example
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client.sip_client import SIPClient


async def main():
    """Basic call example."""
    # Initialize client
    client = SIPClient(config_path="config/client_config.yaml")
    
    # Start client
    client.start()
    
    # Register with server
    print("Registering with SIP server...")
    client.register()
    await asyncio.sleep(1)  # Wait for registration
    
    # Make a call
    print("Making call to sip:user@example.com...")
    call_id = client.make_call("sip:user@example.com")
    
    if call_id:
        print(f"Call initiated: {call_id}")
        
        # Wait for call to connect
        await asyncio.sleep(5)
        
        # Hangup
        print("Hanging up...")
        client.hangup(call_id)
    
    # Keep running for a bit
    await asyncio.sleep(2)
    
    # Stop client
    client.stop()
    print("Client stopped")


if __name__ == "__main__":
    asyncio.run(main())

