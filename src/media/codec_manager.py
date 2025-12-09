"""
Codec Management
"""

from enum import Enum
from typing import Dict, Optional


class Codec(Enum):
    """Audio codecs supported."""
    PCMU = ("PCMU", 0, 8000, "G.711 μ-law")
    PCMA = ("PCMA", 8, 8000, "G.711 A-law")
    G722 = ("G722", 9, 16000, "G.722")
    G729 = ("G729", 18, 8000, "G.729")
    OPUS = ("opus", 111, 48000, "Opus")
    
    def __init__(self, name, payload_type, sample_rate, description):
        self.name = name
        self.payload_type = payload_type
        self.sample_rate = sample_rate
        self.description = description


class CodecManager:
    """Manages audio codecs for SIP sessions."""
    
    def __init__(self, preferred_codecs: Optional[list] = None):
        """
        Initialize codec manager.
        
        Args:
            preferred_codecs: List of preferred codec names (e.g., ['PCMU', 'PCMA'])
        """
        self.preferred_codecs = preferred_codecs or ['PCMU', 'PCMA', 'G722']
        self.available_codecs = {codec.name: codec for codec in Codec}
    
    def get_codec(self, name: str) -> Optional[Codec]:
        """Get a codec by name."""
        return self.available_codecs.get(name.upper())
    
    def negotiate_codec(self, offered_codecs: list) -> Optional[Codec]:
        """
        Negotiate codec from offered list.
        
        Args:
            offered_codecs: List of codec names offered by remote party
            
        Returns:
            Selected codec or None if no match
        """
        # Try preferred codecs in order
        for preferred in self.preferred_codecs:
            for offered in offered_codecs:
                if preferred.upper() == offered.upper():
                    codec = self.get_codec(preferred)
                    if codec:
                        return codec
        
        # If no preferred match, return first available
        for offered in offered_codecs:
            codec = self.get_codec(offered)
            if codec:
                return codec
        
        return None
    
    def generate_sdp_codec_list(self) -> str:
        """Generate SDP codec list for offer/answer."""
        codec_list = []
        for codec_name in self.preferred_codecs:
            codec = self.get_codec(codec_name)
            if codec:
                codec_list.append(f"a=rtpmap:{codec.payload_type} {codec.name}/{codec.sample_rate}")
        return "\r\n".join(codec_list)
    
    def parse_sdp_codecs(self, sdp: str) -> list:
        """Parse codecs from SDP."""
        codecs = []
        lines = sdp.split('\r\n')
        for line in lines:
            if line.startswith('a=rtpmap:'):
                # Format: a=rtpmap:0 PCMU/8000
                parts = line.split(':')
                if len(parts) > 1:
                    rtpmap = parts[1].strip()
                    codec_name = rtpmap.split('/')[0]
                    # Extract codec name from payload type
                    # For now, just try to match by name
                    for codec in Codec:
                        if codec.name.lower() in rtpmap.lower():
                            codecs.append(codec.name)
                            break
        return codecs

