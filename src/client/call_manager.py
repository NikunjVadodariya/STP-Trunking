"""
Call Manager for SIP Client
"""

from typing import Dict, Optional
import time
import logging

logger = logging.getLogger(__name__)


class ClientCall:
    """Represents a call from client perspective."""
    
    def __init__(self, call_id: str, remote_uri: str, local_uri: str):
        self.call_id = call_id
        self.remote_uri = remote_uri
        self.local_uri = local_uri
        self.state = "INITIATING"
        self.created_at = time.time()
        self.connected_at: Optional[float] = None
        self.terminated_at: Optional[float] = None
        
        self.local_tag: Optional[str] = None
        self.remote_tag: Optional[str] = None
        self.local_sdp: Optional[str] = None
        self.remote_sdp: Optional[str] = None
        
        self.local_rtp_ip: Optional[str] = None
        self.local_rtp_port: Optional[int] = None
        self.remote_rtp_ip: Optional[str] = None
        self.remote_rtp_port: Optional[int] = None
    
    def set_state(self, state: str):
        """Update call state."""
        self.state = state
        if state == "CONNECTED" and not self.connected_at:
            self.connected_at = time.time()
        elif state == "TERMINATED" and not self.terminated_at:
            self.terminated_at = time.time()
    
    def get_duration(self) -> float:
        """Get call duration in seconds."""
        if self.connected_at and self.terminated_at:
            return self.terminated_at - self.connected_at
        elif self.connected_at:
            return time.time() - self.connected_at
        return 0.0


class CallManager:
    """Manages calls for SIP client."""
    
    def __init__(self):
        self.calls: Dict[str, ClientCall] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_call(self, call_id: str, remote_uri: str, local_uri: str) -> ClientCall:
        """Create a new call."""
        call = ClientCall(call_id, remote_uri, local_uri)
        self.calls[call_id] = call
        self.logger.info(f"Created call {call_id}: {local_uri} -> {remote_uri}")
        return call
    
    def get_call(self, call_id: str) -> Optional[ClientCall]:
        """Get a call by ID."""
        return self.calls.get(call_id)
    
    def remove_call(self, call_id: str):
        """Remove a call."""
        if call_id in self.calls:
            call = self.calls[call_id]
            call.set_state("TERMINATED")
            del self.calls[call_id]
            self.logger.info(f"Removed call {call_id}")
    
    def get_active_calls(self) -> list:
        """Get list of active calls."""
        return [call for call in self.calls.values() if call.state != "TERMINATED"]

