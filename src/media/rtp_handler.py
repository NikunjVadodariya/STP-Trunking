"""
RTP (Real-time Transport Protocol) Handler
"""

import socket
import struct
import threading
import time
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class RTPPacket:
    """RTP Packet structure."""
    
    def __init__(self, payload_type=0, sequence_number=0, timestamp=0, 
                 ssrc=0, payload=b''):
        self.version = 2
        self.padding = 0
        self.extension = 0
        self.cc = 0  # CSRC count
        self.marker = 0
        self.payload_type = payload_type
        self.sequence_number = sequence_number
        self.timestamp = timestamp
        self.ssrc = ssrc
        self.csrc_list = []
        self.payload = payload
    
    def pack(self) -> bytes:
        """Pack RTP packet into bytes."""
        # RTP header (12 bytes minimum)
        header = struct.pack('!BBHII',
                            (self.version << 6) | (self.padding << 5) | 
                            (self.extension << 4) | self.cc,
                            (self.marker << 7) | self.payload_type,
                            self.sequence_number,
                            self.timestamp,
                            self.ssrc)
        
        # Add CSRC list if present
        csrc_data = b''
        for csrc in self.csrc_list:
            csrc_data += struct.pack('!I', csrc)
        
        return header + csrc_data + self.payload
    
    @classmethod
    def unpack(cls, data: bytes) -> 'RTPPacket':
        """Unpack bytes into RTP packet."""
        if len(data) < 12:
            raise ValueError("RTP packet too short")
        
        # Parse header
        byte1, byte2, seq, ts, ssrc = struct.unpack('!BBHII', data[:12])
        
        version = (byte1 >> 6) & 0x3
        padding = (byte1 >> 5) & 0x1
        extension = (byte1 >> 4) & 0x1
        cc = byte1 & 0xF
        
        marker = (byte2 >> 7) & 0x1
        payload_type = byte2 & 0x7F
        
        # Parse CSRC list
        csrc_list = []
        offset = 12
        for _ in range(cc):
            if len(data) >= offset + 4:
                csrc = struct.unpack('!I', data[offset:offset+4])[0]
                csrc_list.append(csrc)
                offset += 4
        
        # Payload is the rest
        payload = data[offset:]
        
        packet = cls(payload_type, seq, ts, ssrc, payload)
        packet.version = version
        packet.padding = padding
        packet.extension = extension
        packet.cc = cc
        packet.marker = marker
        packet.csrc_list = csrc_list
        
        return packet


class RTPHandler:
    """Handles RTP packet transmission and reception."""
    
    def __init__(self, local_ip: str = "0.0.0.0", local_port: int = 0,
                 remote_ip: Optional[str] = None, remote_port: Optional[int] = None):
        """
        Initialize RTP handler.
        
        Args:
            local_ip: Local IP address to bind to
            local_port: Local port (0 for auto-assign)
            remote_ip: Remote IP address for sending
            remote_port: Remote port for sending
        """
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        
        self.sequence_number = 0
        self.timestamp = 0
        self.ssrc = int(time.time()) & 0xFFFFFFFF
        
        self.on_packet_received: Optional[Callable[[RTPPacket], None]] = None
        self.sample_rate = 8000  # Default sample rate
    
    def start(self):
        """Start RTP handler."""
        if self.running:
            return
        
        # Create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.local_ip, self.local_port))
        
        # Get actual port if auto-assigned
        self.local_port = self.socket.getsockname()[1]
        
        self.running = True
        
        # Start receive thread
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        
        logger.info(f"RTP handler started on {self.local_ip}:{self.local_port}")
    
    def stop(self):
        """Stop RTP handler."""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)
        logger.info("RTP handler stopped")
    
    def set_remote(self, ip: str, port: int):
        """Set remote RTP endpoint."""
        self.remote_ip = ip
        self.remote_port = port
        logger.info(f"RTP remote set to {ip}:{port}")
    
    def send_packet(self, payload: bytes, payload_type: int = 0, marker: int = 0):
        """Send an RTP packet."""
        if not self.running or not self.socket or not self.remote_ip or not self.remote_port:
            return False
        
        packet = RTPPacket(
            payload_type=payload_type,
            sequence_number=self.sequence_number,
            timestamp=self.timestamp,
            ssrc=self.ssrc,
            payload=payload
        )
        packet.marker = marker
        
        try:
            data = packet.pack()
            self.socket.sendto(data, (self.remote_ip, self.remote_port))
            
            self.sequence_number = (self.sequence_number + 1) & 0xFFFF
            # Increment timestamp based on sample rate
            # Assuming 20ms packets (160 samples at 8kHz)
            self.timestamp += len(payload)  # Simplified
            
            return True
        except Exception as e:
            logger.error(f"Error sending RTP packet: {e}")
            return False
    
    def _receive_loop(self):
        """Receive loop running in separate thread."""
        while self.running and self.socket:
            try:
                data, addr = self.socket.recvfrom(1500)
                packet = RTPPacket.unpack(data)
                
                if self.on_packet_received:
                    self.on_packet_received(packet)
            except socket.error:
                if self.running:
                    logger.error("Socket error in receive loop")
                break
            except Exception as e:
                logger.error(f"Error receiving RTP packet: {e}")
    
    def set_sample_rate(self, sample_rate: int):
        """Set audio sample rate."""
        self.sample_rate = sample_rate
    
    def set_on_packet_received(self, callback: Callable[[RTPPacket], None]):
        """Set callback for received packets."""
        self.on_packet_received = callback

