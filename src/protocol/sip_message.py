"""
SIP Message Classes
"""

from typing import Dict, Optional, List
from enum import Enum
import time


class SIPMethod(Enum):
    """SIP Methods"""
    INVITE = "INVITE"
    ACK = "ACK"
    BYE = "BYE"
    CANCEL = "CANCEL"
    REGISTER = "REGISTER"
    OPTIONS = "OPTIONS"
    INFO = "INFO"
    UPDATE = "UPDATE"
    PRACK = "PRACK"
    REFER = "REFER"
    NOTIFY = "NOTIFY"
    SUBSCRIBE = "SUBSCRIBE"


class SIPStatusCode(Enum):
    """SIP Status Codes"""
    # 1xx Provisional
    TRYING = (100, "Trying")
    RINGING = (180, "Ringing")
    CALL_IS_BEING_FORWARDED = (181, "Call Is Being Forwarded")
    QUEUED = (182, "Queued")
    SESSION_PROGRESS = (183, "Session Progress")
    
    # 2xx Success
    OK = (200, "OK")
    
    # 3xx Redirection
    MULTIPLE_CHOICES = (300, "Multiple Choices")
    MOVED_PERMANENTLY = (301, "Moved Permanently")
    MOVED_TEMPORARILY = (302, "Moved Temporarily")
    USE_PROXY = (305, "Use Proxy")
    ALTERNATIVE_SERVICE = (380, "Alternative Service")
    
    # 4xx Client Error
    BAD_REQUEST = (400, "Bad Request")
    UNAUTHORIZED = (401, "Unauthorized")
    PAYMENT_REQUIRED = (402, "Payment Required")
    FORBIDDEN = (403, "Forbidden")
    NOT_FOUND = (404, "Not Found")
    METHOD_NOT_ALLOWED = (405, "Method Not Allowed")
    NOT_ACCEPTABLE = (406, "Not Acceptable")
    PROXY_AUTHENTICATION_REQUIRED = (407, "Proxy Authentication Required")
    REQUEST_TIMEOUT = (408, "Request Timeout")
    GONE = (410, "Gone")
    REQUEST_ENTITY_TOO_LARGE = (413, "Request Entity Too Large")
    REQUEST_URI_TOO_LONG = (414, "Request-URI Too Long")
    UNSUPPORTED_MEDIA_TYPE = (415, "Unsupported Media Type")
    UNSUPPORTED_URI_SCHEME = (416, "Unsupported URI Scheme")
    BAD_EXTENSION = (420, "Bad Extension")
    EXTENSION_REQUIRED = (421, "Extension Required")
    INTERVAL_TOO_BRIEF = (423, "Interval Too Brief")
    TEMPORARILY_UNAVAILABLE = (480, "Temporarily Unavailable")
    CALL_OR_TRANSACTION_DOES_NOT_EXIST = (481, "Call/Transaction Does Not Exist")
    LOOP_DETECTED = (482, "Loop Detected")
    TOO_MANY_HOPS = (483, "Too Many Hops")
    ADDRESS_INCOMPLETE = (484, "Address Incomplete")
    AMBIGUOUS = (485, "Ambiguous")
    BUSY_HERE = (486, "Busy Here")
    REQUEST_TERMINATED = (487, "Request Terminated")
    NOT_ACCEPTABLE_HERE = (488, "Not Acceptable Here")
    BAD_EVENT = (489, "Bad Event")
    REQUEST_PENDING = (491, "Request Pending")
    UNDECIPHERABLE = (493, "Undecipherable")
    
    # 5xx Server Error
    INTERNAL_SERVER_ERROR = (500, "Internal Server Error")
    NOT_IMPLEMENTED = (501, "Not Implemented")
    BAD_GATEWAY = (502, "Bad Gateway")
    SERVICE_UNAVAILABLE = (503, "Service Unavailable")
    GATEWAY_TIMEOUT = (504, "Gateway Timeout")
    VERSION_NOT_SUPPORTED = (505, "Version Not Supported")
    MESSAGE_TOO_LARGE = (513, "Message Too Large")
    
    # 6xx Global Failure
    BUSY_EVERYWHERE = (600, "Busy Everywhere")
    DECLINE = (603, "Decline")
    DOES_NOT_EXIST_ANYWHERE = (604, "Does Not Exist Anywhere")
    NOT_ACCEPTABLE_ANYWHERE = (606, "Not Acceptable Anywhere")


class SIPMessage:
    """Base class for SIP messages."""
    
    def __init__(self):
        self.headers: Dict[str, str] = {}
        self.body: str = ""
        self.version = "SIP/2.0"
        self.timestamp = time.time()
    
    def add_header(self, name: str, value: str):
        """Add a header to the message."""
        self.headers[name] = value
    
    def get_header(self, name: str) -> Optional[str]:
        """Get a header value."""
        return self.headers.get(name)
    
    def remove_header(self, name: str):
        """Remove a header."""
        if name in self.headers:
            del self.headers[name]
    
    def to_string(self) -> str:
        """Convert message to string format."""
        raise NotImplementedError
    
    def __str__(self):
        return self.to_string()


class SIPRequest(SIPMessage):
    """SIP Request message."""
    
    def __init__(self, method: SIPMethod, request_uri: str):
        super().__init__()
        self.method = method
        self.request_uri = request_uri
    
    def to_string(self) -> str:
        """Convert request to string format."""
        lines = [f"{self.method.value} {self.request_uri} {self.version}"]
        
        # Add headers
        for name, value in self.headers.items():
            lines.append(f"{name}: {value}")
        
        # Empty line before body
        lines.append("")
        
        # Add body if present
        if self.body:
            lines.append(self.body)
        
        return "\r\n".join(lines) + "\r\n"
    
    @classmethod
    def create_invite(cls, request_uri: str, from_uri: str, to_uri: str, 
                     call_id: str, cseq: int, contact: str, 
                     via: str, max_forwards: int = 70):
        """Create an INVITE request."""
        request = cls(SIPMethod.INVITE, request_uri)
        request.add_header("Via", via)
        request.add_header("From", f"{from_uri};tag={cls._generate_tag()}")
        request.add_header("To", to_uri)
        request.add_header("Call-ID", call_id)
        request.add_header("CSeq", f"{cseq} INVITE")
        request.add_header("Contact", contact)
        request.add_header("Max-Forwards", str(max_forwards))
        request.add_header("Content-Type", "application/sdp")
        request.add_header("User-Agent", "SIP-Trunking/1.0")
        return request
    
    @classmethod
    def create_register(cls, request_uri: str, from_uri: str, to_uri: str,
                       call_id: str, cseq: int, contact: str, via: str,
                       expires: int = 3600):
        """Create a REGISTER request."""
        request = cls(SIPMethod.REGISTER, request_uri)
        request.add_header("Via", via)
        request.add_header("From", f"{from_uri};tag={cls._generate_tag()}")
        request.add_header("To", to_uri)
        request.add_header("Call-ID", call_id)
        request.add_header("CSeq", f"{cseq} REGISTER")
        request.add_header("Contact", f"{contact};expires={expires}")
        request.add_header("Max-Forwards", "70")
        request.add_header("User-Agent", "SIP-Trunking/1.0")
        return request
    
    @classmethod
    def create_bye(cls, request_uri: str, from_uri: str, to_uri: str,
                   call_id: str, cseq: int, via: str, from_tag: str, to_tag: str):
        """Create a BYE request."""
        request = cls(SIPMethod.BYE, request_uri)
        request.add_header("Via", via)
        request.add_header("From", f"{from_uri};tag={from_tag}")
        request.add_header("To", f"{to_uri};tag={to_tag}")
        request.add_header("Call-ID", call_id)
        request.add_header("CSeq", f"{cseq} BYE")
        request.add_header("Max-Forwards", "70")
        return request
    
    @staticmethod
    def _generate_tag():
        """Generate a tag (simplified)."""
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


class SIPResponse(SIPMessage):
    """SIP Response message."""
    
    def __init__(self, status_code: SIPStatusCode, request_method: str = ""):
        super().__init__()
        self.status_code = status_code
        self.request_method = request_method
    
    def to_string(self) -> str:
        """Convert response to string format."""
        code, reason = self.status_code.value
        lines = [f"{self.version} {code} {reason}"]
        
        # Add headers
        for name, value in self.headers.items():
            lines.append(f"{name}: {value}")
        
        # Empty line before body
        lines.append("")
        
        # Add body if present
        if self.body:
            lines.append(self.body)
        
        return "\r\n".join(lines) + "\r\n"
    
    @classmethod
    def create_ok(cls, request: SIPRequest, to_tag: str = None, 
                  contact: str = None, body: str = None):
        """Create a 200 OK response."""
        response = cls(SIPStatusCode.OK, request.method.value)
        
        # Copy Via header
        if request.get_header("Via"):
            response.add_header("Via", request.get_header("Via"))
        
        # Copy From header
        if request.get_header("From"):
            response.add_header("From", request.get_header("From"))
        
        # Copy To header and add tag
        to_header = request.get_header("To")
        if to_header:
            if to_tag and "tag=" not in to_header:
                to_header = f"{to_header};tag={to_tag}"
            response.add_header("To", to_header)
        
        # Copy Call-ID
        if request.get_header("Call-ID"):
            response.add_header("Call-ID", request.get_header("Call-ID"))
        
        # Copy CSeq
        if request.get_header("CSeq"):
            response.add_header("CSeq", request.get_header("CSeq"))
        
        # Add Contact if provided
        if contact:
            response.add_header("Contact", contact)
        
        # Add body if provided
        if body:
            response.body = body
            response.add_header("Content-Type", "application/sdp")
            response.add_header("Content-Length", str(len(body)))
        
        return response
    
    @classmethod
    def create_ringing(cls, request: SIPRequest, to_tag: str = None):
        """Create a 180 Ringing response."""
        response = cls(SIPStatusCode.RINGING, request.method.value)
        
        # Copy headers similar to OK
        if request.get_header("Via"):
            response.add_header("Via", request.get_header("Via"))
        if request.get_header("From"):
            response.add_header("From", request.get_header("From"))
        
        to_header = request.get_header("To")
        if to_header:
            if to_tag and "tag=" not in to_header:
                to_header = f"{to_header};tag={to_tag}"
            response.add_header("To", to_header)
        if request.get_header("Call-ID"):
            response.add_header("Call-ID", request.get_header("Call-ID"))
        if request.get_header("CSeq"):
            response.add_header("CSeq", request.get_header("CSeq"))
        
        return response

