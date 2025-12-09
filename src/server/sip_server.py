"""
SIP Server Implementation
"""

import socket
import threading
import logging
import yaml
import time
from typing import Dict, Optional, Callable
from pathlib import Path

from ..protocol.sip_parser import SIPParser
from ..protocol.sip_message import SIPRequest, SIPResponse, SIPMethod, SIPStatusCode
from ..protocol.sip_utils import generate_tag, generate_branch, parse_sip_uri
from .call_handler import CallHandler, CallState

logger = logging.getLogger(__name__)


class SIPServer:
    """SIP Server for handling SIP requests and responses."""
    
    def __init__(self, config_path: str = "config/server_config.yaml"):
        """
        Initialize SIP server.
        
        Args:
            config_path: Path to server configuration file
        """
        self.config = self._load_config(config_path)
        self.host = self.config.get('host', '0.0.0.0')
        self.port = self.config.get('port', 5060)
        self.domain = self.config.get('domain', 'localhost')
        self.realm = self.config.get('realm', self.domain)
        
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        
        self.call_handler = CallHandler()
        self.registered_users: Dict[str, Dict] = {}  # username -> registration info
        
        self.on_incoming_call: Optional[Callable[[str, str, str], None]] = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")
        return {}
    
    def start(self):
        """Start the SIP server."""
        if self.running:
            logger.warning("Server is already running")
            return
        
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            
            self.running = True
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            logger.info(f"SIP Server started on {self.host}:{self.port}")
            logger.info(f"Domain: {self.domain}")
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the SIP server."""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.receive_thread:
            self.receive_thread.join(timeout=2.0)
        logger.info("SIP Server stopped")
    
    def _receive_loop(self):
        """Main receive loop running in separate thread."""
        while self.running and self.socket:
            try:
                data, addr = self.socket.recvfrom(4096)
                message_str = data.decode('utf-8', errors='ignore')
                
                # Parse SIP message
                message = SIPParser.parse(message_str)
                if message:
                    self._handle_message(message, addr)
                else:
                    logger.warning(f"Failed to parse message from {addr}")
            except socket.error:
                if self.running:
                    logger.error("Socket error in receive loop")
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
    
    def _handle_message(self, message: SIPMessage, addr: tuple):
        """Handle incoming SIP message."""
        if isinstance(message, SIPRequest):
            self._handle_request(message, addr)
        elif isinstance(message, SIPResponse):
            self._handle_response(message, addr)
    
    def _handle_request(self, request: SIPRequest, addr: tuple):
        """Handle incoming SIP request."""
        logger.info(f"Received {request.method.value} from {addr[0]}:{addr[1]}")
        
        if request.method == SIPMethod.REGISTER:
            self._handle_register(request, addr)
        elif request.method == SIPMethod.INVITE:
            self._handle_invite(request, addr)
        elif request.method == SIPMethod.ACK:
            self._handle_ack(request, addr)
        elif request.method == SIPMethod.BYE:
            self._handle_bye(request, addr)
        elif request.method == SIPMethod.CANCEL:
            self._handle_cancel(request, addr)
        elif request.method == SIPMethod.OPTIONS:
            self._handle_options(request, addr)
        else:
            logger.warning(f"Unhandled method: {request.method.value}")
            self._send_response(request, SIPStatusCode.NOT_IMPLEMENTED, addr)
    
    def _handle_register(self, request: SIPRequest, addr: tuple):
        """Handle REGISTER request."""
        from_header = request.get_header("From")
        to_header = request.get_header("To")
        contact_header = request.get_header("Contact")
        
        if not from_header or not to_header:
            self._send_response(request, SIPStatusCode.BAD_REQUEST, addr)
            return
        
        # Extract username from From header
        from_uri = parse_sip_uri(from_header.split(';')[0].strip())
        if not from_uri:
            self._send_response(request, SIPStatusCode.BAD_REQUEST, addr)
            return
        
        username = from_uri.get('user')
        if not username:
            self._send_response(request, SIPStatusCode.BAD_REQUEST, addr)
            return
        
        # For now, accept all registrations (no authentication)
        # In production, implement digest authentication
        
        # Store registration
        self.registered_users[username] = {
            'contact': contact_header or f"sip:{username}@{addr[0]}:{addr[1]}",
            'address': addr,
            'expires': 3600,  # Default expiry
            'registered_at': time.time()
        }
        
        logger.info(f"User {username} registered from {addr[0]}:{addr[1]}")
        
        # Send 200 OK
        response = SIPResponse.create_ok(request, contact=contact_header)
        self._send_message(response, addr)
    
    def _handle_invite(self, request: SIPRequest, addr: tuple):
        """Handle INVITE request."""
        call_id = request.get_header("Call-ID")
        from_header = request.get_header("From")
        to_header = request.get_header("To")
        
        if not call_id or not from_header or not to_header:
            self._send_response(request, SIPStatusCode.BAD_REQUEST, addr)
            return
        
        # Extract URIs
        from_uri = from_header.split(';')[0].strip()
        to_uri = to_header.split(';')[0].strip()
        
        # Create or get call
        call = self.call_handler.get_call(call_id)
        if not call:
            call = self.call_handler.create_call(call_id, from_uri, to_uri)
        
        # Extract tags
        from_tag = SIPParser.extract_tag(from_header)
        to_tag = generate_tag()
        
        call.from_tag = from_tag
        call.to_tag = to_tag
        call.remote_sdp = request.body
        call.set_state(CallState.TRYING)
        
        # Parse SDP to extract RTP info
        if request.body:
            self._parse_sdp_for_rtp(request.body, call)
        
        # Send 100 Trying
        trying_response = SIPResponse(SIPStatusCode.TRYING, request.method.value)
        trying_response.add_header("Via", request.get_header("Via"))
        trying_response.add_header("From", from_header)
        trying_response.add_header("To", to_header)
        trying_response.add_header("Call-ID", call_id)
        trying_response.add_header("CSeq", request.get_header("CSeq"))
        self._send_message(trying_response, addr)
        
        # Send 180 Ringing
        call.set_state(CallState.RINGING)
        ringing_response = SIPResponse.create_ringing(request, to_tag)
        self._send_message(ringing_response, addr)
        
        # Notify about incoming call
        if self.on_incoming_call:
            self.on_incoming_call(call_id, from_uri, to_uri)
        
        # For demo purposes, auto-answer after a short delay
        # In production, this would wait for user interaction
        import threading
        threading.Timer(1.0, self._auto_answer_invite, args=(request, addr, call, to_tag)).start()
    
    def _auto_answer_invite(self, request: SIPRequest, addr: tuple, call, to_tag: str):
        """Auto-answer an INVITE (for demo purposes)."""
        if call.state != CallState.RINGING:
            return
        
        # Generate SDP answer
        sdp_answer = self._generate_sdp_answer(call)
        call.local_sdp = sdp_answer
        
        # Send 200 OK
        ok_response = SIPResponse.create_ok(request, to_tag, 
                                           contact=f"sip:server@{self.domain}:{self.port}",
                                           body=sdp_answer)
        self._send_message(ok_response, addr)
        
        call.set_state(CallState.CONNECTED)
        logger.info(f"Call {call.call_id} connected")
    
    def _handle_ack(self, request: SIPRequest, addr: tuple):
        """Handle ACK request."""
        call_id = request.get_header("Call-ID")
        call = self.call_handler.get_call(call_id)
        if call:
            logger.info(f"ACK received for call {call_id}")
            # ACK confirms the session is established
            call.set_state(CallState.CONNECTED)
    
    def _handle_bye(self, request: SIPRequest, addr: tuple):
        """Handle BYE request."""
        call_id = request.get_header("Call-ID")
        call = self.call_handler.get_call(call_id)
        
        if call:
            call.set_state(CallState.TERMINATED)
            # Send 200 OK
            ok_response = SIPResponse.create_ok(request)
            self._send_message(ok_response, addr)
            self.call_handler.remove_call(call_id)
            logger.info(f"Call {call_id} terminated")
        else:
            # Call not found
            self._send_response(request, SIPStatusCode.CALL_OR_TRANSACTION_DOES_NOT_EXIST, addr)
    
    def _handle_cancel(self, request: SIPRequest, addr: tuple):
        """Handle CANCEL request."""
        call_id = request.get_header("Call-ID")
        call = self.call_handler.get_call(call_id)
        
        if call:
            call.set_state(CallState.TERMINATED)
            # Send 200 OK for CANCEL
            ok_response = SIPResponse.create_ok(request)
            self._send_message(ok_response, addr)
            # Also send 487 Request Terminated for the original INVITE
            self.call_handler.remove_call(call_id)
        else:
            self._send_response(request, SIPStatusCode.CALL_OR_TRANSACTION_DOES_NOT_EXIST, addr)
    
    def _handle_options(self, request: SIPRequest, addr: tuple):
        """Handle OPTIONS request."""
        # Send 200 OK with capabilities
        ok_response = SIPResponse.create_ok(request)
        ok_response.add_header("Allow", "INVITE, ACK, BYE, CANCEL, REGISTER, OPTIONS")
        self._send_message(ok_response, addr)
    
    def _handle_response(self, response: SIPResponse, addr: tuple):
        """Handle incoming SIP response."""
        logger.info(f"Received {response.status_code.value[0]} response")
        # Server typically doesn't handle responses, but could for proxy scenarios
    
    def _send_response(self, request: SIPRequest, status_code: SIPStatusCode, addr: tuple):
        """Send a SIP response."""
        response = SIPResponse(status_code, request.method.value)
        
        # Copy necessary headers
        if request.get_header("Via"):
            response.add_header("Via", request.get_header("Via"))
        if request.get_header("From"):
            response.add_header("From", request.get_header("From"))
        if request.get_header("To"):
            response.add_header("To", request.get_header("To"))
        if request.get_header("Call-ID"):
            response.add_header("Call-ID", request.get_header("Call-ID"))
        if request.get_header("CSeq"):
            response.add_header("CSeq", request.get_header("CSeq"))
        
        self._send_message(response, addr)
    
    def _send_message(self, message: SIPMessage, addr: tuple):
        """Send a SIP message."""
        if not self.socket:
            return
        
        try:
            message_str = message.to_string()
            data = message_str.encode('utf-8')
            self.socket.sendto(data, addr)
            logger.debug(f"Sent {type(message).__name__} to {addr[0]}:{addr[1]}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    def _parse_sdp_for_rtp(self, sdp: str, call):
        """Parse SDP to extract RTP connection info."""
        lines = sdp.split('\r\n')
        for line in lines:
            if line.startswith('c=IN IP4 '):
                # Connection line: c=IN IP4 192.168.1.1
                ip = line.split()[2]
                call.remote_rtp_ip = ip
            elif line.startswith('m=audio '):
                # Media line: m=audio 1234 RTP/AVP 0 8
                parts = line.split()
                if len(parts) > 1:
                    try:
                        port = int(parts[1])
                        call.remote_rtp_port = port
                    except ValueError:
                        pass
    
    def _generate_sdp_answer(self, call) -> str:
        """Generate SDP answer."""
        # Simple SDP generation
        import socket
        local_ip = socket.gethostbyname(socket.gethostname())
        local_rtp_port = 10000  # Default RTP port
        
        sdp = f"""v=0
o=- 0 0 IN IP4 {local_ip}
s=SIP Call
c=IN IP4 {local_ip}
t=0 0
m=audio {local_rtp_port} RTP/AVP 0 8
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=sendrecv
"""
        return sdp
    
    def set_on_incoming_call(self, callback: Callable[[str, str, str], None]):
        """Set callback for incoming calls."""
        self.on_incoming_call = callback

