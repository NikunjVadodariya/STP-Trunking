"""
SIP Client Implementation
"""

import socket
import threading
import logging
import yaml
import time
from typing import Optional, Callable
from pathlib import Path

from ..protocol.sip_parser import SIPParser
from ..protocol.sip_message import SIPMessage, SIPRequest, SIPResponse, SIPMethod, SIPStatusCode
from ..protocol.sip_utils import generate_tag, generate_branch, generate_call_id, build_sip_uri, parse_sip_uri
from .call_manager import CallManager, ClientCall

logger = logging.getLogger(__name__)


class SIPClient:
    """SIP Client for making and receiving calls."""
    
    def __init__(self, config_path: str = "config/client_config.yaml"):
        """
        Initialize SIP client.
        
        Args:
            config_path: Path to client configuration file
        """
        self.config = self._load_config(config_path)
        # Handle nested config structure (from call_service) or flat structure (from file)
        client_config = self.config.get('client', self.config)
        self.server_host = client_config.get('server_host', 'localhost')
        self.server_port = client_config.get('server_port', 5060)
        self.username = client_config.get('username', 'user')
        self.password = client_config.get('password', '')
        self.domain = client_config.get('domain', 'localhost')
        
        self.local_ip = client_config.get('local_ip', '0.0.0.0')
        self.local_port = client_config.get('local_port', 0)  # 0 for auto-assign
        
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        
        self.call_manager = CallManager()
        self.registered = False
        self.cseq = 1
        self.local_tag = generate_tag()
        
        self.on_incoming_call: Optional[Callable[[str, str], None]] = None
        self.on_call_connected: Optional[Callable[[str], None]] = None
        self.on_call_ended: Optional[Callable[[str], None]] = None
        self.on_call_ringing: Optional[Callable[[str], None]] = None
        self.on_call_trying: Optional[Callable[[str], None]] = None
        
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
        """Start the SIP client."""
        if self.running:
            logger.warning("Client is already running")
            return
        
        try:
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
            
            logger.info(f"SIP Client started on {self.local_ip}:{self.local_port}")
        except Exception as e:
            logger.error(f"Failed to start client: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the SIP client."""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.receive_thread:
            self.receive_thread.join(timeout=2.0)
        logger.info("SIP Client stopped")
    
    def register(self, expires: int = 3600):
        """Register with SIP server."""
        if not self.running:
            self.start()
        
        # Resolve server hostname to IP
        try:
            server_ip = socket.gethostbyname(self.server_host)
        except (socket.gaierror, OSError) as e:
            error_msg = f"Cannot resolve SIP server hostname '{self.server_host}': {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        
        request_uri = build_sip_uri(host=self.domain, port=self.server_port)
        from_uri = build_sip_uri(user=self.username, host=self.domain)
        to_uri = from_uri
        call_id = generate_call_id()
        
        # Get local IP
        import socket as sock
        try:
            local_ip = sock.gethostbyname(sock.gethostname())
        except (socket.gaierror, OSError):
            # Fallback: connect to external address to determine local IP
            try:
                s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                local_ip = "127.0.0.1"  # Final fallback
        contact = build_sip_uri(user=self.username, host=local_ip, port=self.local_port)
        
        via = f"SIP/2.0/UDP {local_ip}:{self.local_port};branch={generate_branch()}"
        
        request = SIPRequest.create_register(
            request_uri=request_uri,
            from_uri=from_uri,
            to_uri=to_uri,
            call_id=call_id,
            cseq=self.cseq,
            contact=contact,
            via=via,
            expires=expires
        )
        
        self.cseq += 1
        
        # Send request to resolved IP
        self._send_request(request, (server_ip, self.server_port))
        
        # Wait for response (simplified - in production, use proper transaction handling)
        logger.info(f"Registration request sent for {self.username} to {server_ip}:{self.server_port}")
    
    def make_call(self, remote_uri: str) -> Optional[str]:
        """
        Make a call to remote URI.
        
        Args:
            remote_uri: SIP URI to call (e.g., 'sip:user@example.com')
            
        Returns:
            Call ID if successful, None otherwise
        """
        if not self.running:
            self.start()
        
        if not self.registered:
            logger.warning("Not registered. Attempting registration...")
            self.register()
            time.sleep(0.5)  # Wait a bit for registration
        
        # Generate call ID
        call_id = generate_call_id()
        
        # Parse remote URI
        remote = parse_sip_uri(remote_uri)
        if not remote:
            logger.error(f"Invalid remote URI: {remote_uri}")
            return None
        
        # Build URIs
        request_uri = remote_uri
        from_uri = build_sip_uri(user=self.username, host=self.domain)
        to_uri = remote_uri
        
        # Get local IP
        import socket as sock
        try:
            local_ip = sock.gethostbyname(sock.gethostname())
        except (socket.gaierror, OSError):
            # Fallback: connect to external address to determine local IP
            try:
                s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                local_ip = "127.0.0.1"  # Final fallback
        contact = build_sip_uri(user=self.username, host=local_ip, port=self.local_port)
        
        via = f"SIP/2.0/UDP {local_ip}:{self.local_port};branch={generate_branch()}"
        
        # Generate SDP offer
        sdp_offer = self._generate_sdp_offer(local_ip)
        
        # Create INVITE request
        request = SIPRequest.create_invite(
            request_uri=request_uri,
            from_uri=from_uri,
            to_uri=to_uri,
            call_id=call_id,
            cseq=self.cseq,
            contact=contact,
            via=via
        )
        request.body = sdp_offer
        request.add_header("Content-Type", "application/sdp")
        request.add_header("Content-Length", str(len(sdp_offer)))
        
        self.cseq += 1
        
        # Create call
        call = self.call_manager.create_call(call_id, remote_uri, from_uri)
        call.local_tag = self.local_tag
        call.local_sdp = sdp_offer
        call.set_state("INITIATING")
        
        # Resolve server hostname and send INVITE
        try:
            server_ip = socket.gethostbyname(self.server_host)
        except (socket.gaierror, OSError) as e:
            error_msg = f"Cannot resolve SIP server hostname '{self.server_host}': {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        
        self._send_request(request, (server_ip, self.server_port))
        
        logger.info(f"Call initiated: {call_id} -> {remote_uri}")
        return call_id
    
    def hangup(self, call_id: str):
        """Hang up a call."""
        call = self.call_manager.get_call(call_id)
        if not call:
            logger.warning(f"Call {call_id} not found")
            return
        
        # Build BYE request
        request_uri = call.remote_uri
        from_uri = call.local_uri
        to_uri = call.remote_uri
        
        import socket as sock
        try:
            local_ip = sock.gethostbyname(sock.gethostname())
        except (socket.gaierror, OSError):
            # Fallback: connect to external address to determine local IP
            try:
                s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                local_ip = "127.0.0.1"  # Final fallback
        via = f"SIP/2.0/UDP {local_ip}:{self.local_port};branch={generate_branch()}"
        
        request = SIPRequest.create_bye(
            request_uri=request_uri,
            from_uri=from_uri,
            to_uri=to_uri,
            call_id=call_id,
            cseq=self.cseq,
            via=via,
            from_tag=call.local_tag or self.local_tag,
            to_tag=call.remote_tag or ""
        )
        
        self.cseq += 1
        
        # Send BYE
        self._send_request(request, (self.server_host, self.server_port))
        
        call.set_state("TERMINATED")
        logger.info(f"Hangup sent for call {call_id}")
    
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
        
        if request.method == SIPMethod.INVITE:
            self._handle_incoming_invite(request, addr)
        elif request.method == SIPMethod.BYE:
            self._handle_bye(request, addr)
        elif request.method == SIPMethod.ACK:
            self._handle_ack(request, addr)
        else:
            logger.warning(f"Unhandled request method: {request.method.value}")
    
    def _handle_response(self, response: SIPResponse, addr: tuple):
        """Handle incoming SIP response."""
        call_id = response.get_header("Call-ID")
        call = self.call_manager.get_call(call_id) if call_id else None
        
        status_code, reason = response.status_code.value
        
        logger.info(f"Received {status_code} {reason} for call {call_id}")
        
        if status_code == 200:
            if response.request_method == "REGISTER":
                self.registered = True
                logger.info("Registration successful")
            elif response.request_method == "INVITE":
                if call:
                    # Extract remote tag
                    to_header = response.get_header("To")
                    if to_header:
                        call.remote_tag = SIPParser.extract_tag(to_header)
                    
                    # Extract SDP answer
                    call.remote_sdp = response.body
                    if response.body:
                        self._parse_sdp_for_rtp(response.body, call)
                    
                    call.set_state("CONNECTED")
                    
                    # Send ACK
                    self._send_ack(call, response)
                    
                    if self.on_call_connected:
                        self.on_call_connected(call_id)
        elif status_code == 180:
            # Ringing
            if call:
                call.set_state("RINGING")
                logger.info(f"Call {call_id} is ringing")
                # Trigger callback if set
                if hasattr(self, 'on_call_ringing') and self.on_call_ringing:
                    self.on_call_ringing(call_id)
        elif status_code == 100:
            # Trying
            if call:
                call.set_state("TRYING")
                logger.info(f"Call {call_id} is trying")
                # Trigger callback if set
                if hasattr(self, 'on_call_trying') and self.on_call_trying:
                    self.on_call_trying(call_id)
        elif status_code >= 400:
            # Error response
            if call:
                call.set_state("FAILED")
                logger.error(f"Call {call_id} failed: {status_code} {reason}")
                if self.on_call_ended:
                    self.on_call_ended(call_id)
    
    def _handle_incoming_invite(self, request: SIPRequest, addr: tuple):
        """Handle incoming INVITE (incoming call)."""
        call_id = request.get_header("Call-ID")
        from_header = request.get_header("From")
        to_header = request.get_header("To")
        
        if not call_id or not from_header:
            return
        
        from_uri = from_header.split(';')[0].strip()
        to_uri = to_header.split(';')[0].strip() if to_header else ""
        
        # Create call
        call = self.call_manager.create_call(call_id, from_uri, to_uri)
        call.remote_tag = SIPParser.extract_tag(from_header)
        call.local_tag = generate_tag()
        call.remote_sdp = request.body
        call.set_state("RINGING")
        
        # Notify about incoming call
        if self.on_incoming_call:
            self.on_incoming_call(from_uri, to_uri)
        
        # Send 180 Ringing
        ringing_response = SIPResponse.create_ringing(request, call.local_tag)
        self._send_message(ringing_response, addr)
        
        # For demo, auto-answer after delay
        import threading
        threading.Timer(1.0, self._auto_answer, args=(request, addr, call)).start()
    
    def _auto_answer(self, request: SIPRequest, addr: tuple, call: ClientCall):
        """Auto-answer an incoming call."""
        if call.state != "RINGING":
            return
        
        # Generate SDP answer
        import socket as sock
        try:
            local_ip = sock.gethostbyname(sock.gethostname())
        except (socket.gaierror, OSError):
            # Fallback: connect to external address to determine local IP
            try:
                s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                local_ip = "127.0.0.1"  # Final fallback
        sdp_answer = self._generate_sdp_offer(local_ip)
        call.local_sdp = sdp_answer
        
        # Send 200 OK
        ok_response = SIPResponse.create_ok(request, call.local_tag, body=sdp_answer)
        self._send_message(ok_response, addr)
        
        call.set_state("CONNECTED")
        logger.info(f"Incoming call {call.call_id} answered")
        
        if self.on_call_connected:
            self.on_call_connected(call.call_id)
    
    def _handle_bye(self, request: SIPRequest, addr: tuple):
        """Handle BYE request."""
        call_id = request.get_header("Call-ID")
        call = self.call_manager.get_call(call_id)
        
        if call:
            # Send 200 OK
            ok_response = SIPResponse.create_ok(request)
            self._send_message(ok_response, addr)
            
            call.set_state("TERMINATED")
            self.call_manager.remove_call(call_id)
            
            if self.on_call_ended:
                self.on_call_ended(call_id)
    
    def _handle_ack(self, request: SIPRequest, addr: tuple):
        """Handle ACK request."""
        call_id = request.get_header("Call-ID")
        call = self.call_manager.get_call(call_id)
        if call:
            call.set_state("CONNECTED")
            logger.info(f"ACK received for call {call_id}")
    
    def _send_ack(self, call: ClientCall, response: SIPResponse):
        """Send ACK for 200 OK response."""
        import socket as sock
        try:
            local_ip = sock.gethostbyname(sock.gethostname())
        except (socket.gaierror, OSError):
            # Fallback: connect to external address to determine local IP
            try:
                s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                local_ip = "127.0.0.1"  # Final fallback
        via = f"SIP/2.0/UDP {local_ip}:{self.local_port};branch={generate_branch()}"
        
        ack = SIPRequest(SIPMethod.ACK, call.remote_uri)
        ack.add_header("Via", via)
        ack.add_header("From", f"{call.local_uri};tag={call.local_tag}")
        ack.add_header("To", f"{call.remote_uri};tag={call.remote_tag}")
        ack.add_header("Call-ID", call.call_id)
        ack.add_header("CSeq", f"{self.cseq} ACK")
        ack.add_header("Max-Forwards", "70")
        
        self.cseq += 1
        
        # Send to server
        self._send_request(ack, (self.server_host, self.server_port))
    
    def _send_request(self, request: SIPRequest, addr: tuple):
        """Send a SIP request."""
        if not self.socket:
            return
        
        try:
            message_str = request.to_string()
            data = message_str.encode('utf-8')
            self.socket.sendto(data, addr)
            logger.debug(f"Sent {request.method.value} to {addr[0]}:{addr[1]}")
        except Exception as e:
            logger.error(f"Error sending request: {e}")
    
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
    
    def _generate_sdp_offer(self, local_ip: str) -> str:
        """Generate SDP offer."""
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
    
    def _parse_sdp_for_rtp(self, sdp: str, call: ClientCall):
        """Parse SDP to extract RTP connection info."""
        lines = sdp.split('\r\n')
        for line in lines:
            if line.startswith('c=IN IP4 '):
                ip = line.split()[2]
                call.remote_rtp_ip = ip
            elif line.startswith('m=audio '):
                parts = line.split()
                if len(parts) > 1:
                    try:
                        port = int(parts[1])
                        call.remote_rtp_port = port
                    except ValueError:
                        pass
    
    def set_on_incoming_call(self, callback: Callable[[str, str], None]):
        """Set callback for incoming calls."""
        self.on_incoming_call = callback
    
    def set_on_call_connected(self, callback: Callable[[str], None]):
        """Set callback for call connected."""
        self.on_call_connected = callback
    
    def set_on_call_ended(self, callback: Callable[[str], None]):
        """Set callback for call ended."""
        self.on_call_ended = callback
    
    def set_on_call_ringing(self, callback: Callable[[str], None]):
        """Set callback for call ringing."""
        self.on_call_ringing = callback
    
    def set_on_call_trying(self, callback: Callable[[str], None]):
        """Set callback for call trying."""
        self.on_call_trying = callback

