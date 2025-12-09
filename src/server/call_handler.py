"""
Call Handler for SIP Server
"""

from enum import Enum
from typing import Dict, Optional
import time
import logging

logger = logging.getLogger(__name__)


class CallState(Enum):
    """Call state enumeration."""
    INITIATING = "INITIATING"
    TRYING = "TRYING"
    RINGING = "RINGING"
    CONNECTED = "CONNECTED"
    TERMINATED = "TERMINATED"
    FAILED = "FAILED"


class Call:
    """Represents a SIP call."""
    
    def __init__(self, call_id: str, from_uri: str, to_uri: str):
        self.call_id = call_id
        self.from_uri = from_uri
        self.to_uri = to_uri
        self.state = CallState.INITIATING
        self.created_at = time.time()
        self.connected_at: Optional[float] = None
        self.terminated_at: Optional[float] = None
        
        self.from_tag: Optional[str] = None
        self.to_tag: Optional[str] = None
        self.local_sdp: Optional[str] = None
        self.remote_sdp: Optional[str] = None
        
        self.local_rtp_ip: Optional[str] = None
        self.local_rtp_port: Optional[int] = None
        self.remote_rtp_ip: Optional[str] = None
        self.remote_rtp_port: Optional[int] = None
    
    def set_state(self, state: CallState):
        """Update call state."""
        self.state = state
        if state == CallState.CONNECTED and not self.connected_at:
            self.connected_at = time.time()
        elif state == CallState.TERMINATED and not self.terminated_at:
            self.terminated_at = time.time()
    
    def get_duration(self) -> float:
        """Get call duration in seconds."""
        if self.connected_at and self.terminated_at:
            return self.terminated_at - self.connected_at
        elif self.connected_at:
            return time.time() - self.connected_at
        return 0.0


class CallHandler:
    """Manages active calls."""
    
    def __init__(self):
        self.calls: Dict[str, Call] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_call(self, call_id: str, from_uri: str, to_uri: str) -> Call:
        """Create a new call."""
        call = Call(call_id, from_uri, to_uri)
        self.calls[call_id] = call
        self.logger.info(f"Created call {call_id}: {from_uri} -> {to_uri}")
        return call
    
    def get_call(self, call_id: str) -> Optional[Call]:
        """Get a call by ID."""
        return self.calls.get(call_id)
    
    def remove_call(self, call_id: str):
        """Remove a call."""
        if call_id in self.calls:
            call = self.calls[call_id]
            call.set_state(CallState.TERMINATED)
            del self.calls[call_id]
            self.logger.info(f"Removed call {call_id}")
    
    def get_active_calls(self) -> list:
        """Get list of active calls."""
        return [call for call in self.calls.values() 
                if call.state != CallState.TERMINATED]
    
    def find_call_by_tag(self, from_tag: str, to_tag: str = None) -> Optional[Call]:
        """Find a call by tags."""
        for call in self.calls.values():
            if call.from_tag == from_tag:
                if to_tag is None or call.to_tag == to_tag:
                    return call
        return None

