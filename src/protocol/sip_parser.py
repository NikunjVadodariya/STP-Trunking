"""
SIP Message Parser
"""

import re
from typing import Optional, Dict
from .sip_message import SIPMessage, SIPRequest, SIPResponse, SIPMethod, SIPStatusCode


class SIPParser:
    """Parser for SIP messages."""
    
    # Regex patterns
    REQUEST_LINE = re.compile(r'^([A-Z]+)\s+([^\s]+)\s+(SIP/2\.0)$')
    RESPONSE_LINE = re.compile(r'^(SIP/2\.0)\s+(\d{3})\s+(.+)$')
    HEADER_LINE = re.compile(r'^([^:]+):\s*(.+)$')
    
    @staticmethod
    def parse(message: str) -> Optional[SIPMessage]:
        """Parse a SIP message string into a SIPMessage object."""
        if not message or not message.strip():
            return None
        
        lines = message.split('\r\n')
        if not lines:
            lines = message.split('\n')
        
        # Remove empty lines at the end
        while lines and not lines[-1].strip():
            lines.pop()
        
        if not lines:
            return None
        
        # Parse start line
        start_line = lines[0].strip()
        
        # Check if it's a request or response
        request_match = SIPParser.REQUEST_LINE.match(start_line)
        response_match = SIPParser.RESPONSE_LINE.match(start_line)
        
        if request_match:
            return SIPParser._parse_request(lines)
        elif response_match:
            return SIPParser._parse_response(lines)
        else:
            return None
    
    @staticmethod
    def _parse_request(lines: list) -> SIPRequest:
        """Parse a SIP request."""
        # Parse request line
        request_line = lines[0].strip()
        match = SIPParser.REQUEST_LINE.match(request_line)
        if not match:
            raise ValueError(f"Invalid request line: {request_line}")
        
        method_str, request_uri, version = match.groups()
        
        try:
            method = SIPMethod(method_str)
        except ValueError:
            raise ValueError(f"Unknown SIP method: {method_str}")
        
        request = SIPRequest(method, request_uri)
        request.version = version
        
        # Parse headers
        body_start = None
        for i, line in enumerate(lines[1:], 1):
            line = line.strip()
            
            # Empty line indicates start of body
            if not line:
                body_start = i + 1
                break
            
            # Handle continuation lines (lines starting with space or tab)
            if line.startswith(' ') or line.startswith('\t'):
                # Continuation of previous header
                if request.headers:
                    last_header = list(request.headers.keys())[-1]
                    request.headers[last_header] += ' ' + line.strip()
                continue
            
            # Parse header
            header_match = SIPParser.HEADER_LINE.match(line)
            if header_match:
                header_name, header_value = header_match.groups()
                # Handle multiple headers with same name
                if header_name in request.headers:
                    # Append to existing header (comma-separated)
                    request.headers[header_name] += f", {header_value}"
                else:
                    request.headers[header_name] = header_value
        
        # Parse body
        if body_start and body_start < len(lines):
            request.body = '\r\n'.join(lines[body_start:])
            content_length = request.get_header("Content-Length")
            if content_length:
                try:
                    length = int(content_length.strip())
                    if len(request.body) >= length:
                        request.body = request.body[:length]
                except ValueError:
                    pass
        
        return request
    
    @staticmethod
    def _parse_response(lines: list) -> SIPResponse:
        """Parse a SIP response."""
        # Parse status line
        status_line = lines[0].strip()
        match = SIPParser.RESPONSE_LINE.match(status_line)
        if not match:
            raise ValueError(f"Invalid status line: {status_line}")
        
        version, code_str, reason = match.groups()
        code = int(code_str)
        
        # Find matching status code
        status_code = None
        for sc in SIPStatusCode:
            if sc.value[0] == code:
                status_code = sc
                break
        
        if not status_code:
            # Create a generic status code if not found
            class GenericStatusCode:
                def __init__(self, code, reason):
                    self.value = (code, reason)
            status_code = GenericStatusCode(code, reason)
        
        response = SIPResponse(status_code, "")
        response.version = version
        
        # Get request method from CSeq header (will parse later)
        request_method = ""
        
        # Parse headers
        body_start = None
        for i, line in enumerate(lines[1:], 1):
            line = line.strip()
            
            # Empty line indicates start of body
            if not line:
                body_start = i + 1
                break
            
            # Handle continuation lines
            if line.startswith(' ') or line.startswith('\t'):
                if response.headers:
                    last_header = list(response.headers.keys())[-1]
                    response.headers[last_header] += ' ' + line.strip()
                continue
            
            # Parse header
            header_match = SIPParser.HEADER_LINE.match(line)
            if header_match:
                header_name, header_value = header_match.groups()
                
                # Extract request method from CSeq
                if header_name.lower() == "cseq":
                    parts = header_value.split()
                    if len(parts) > 0:
                        request_method = parts[-1]
                        response.request_method = request_method
                
                # Handle multiple headers with same name
                if header_name in response.headers:
                    response.headers[header_name] += f", {header_value}"
                else:
                    response.headers[header_name] = header_value
        
        # Parse body
        if body_start and body_start < len(lines):
            response.body = '\r\n'.join(lines[body_start:])
            content_length = response.get_header("Content-Length")
            if content_length:
                try:
                    length = int(content_length.strip())
                    if len(response.body) >= length:
                        response.body = response.body[:length]
                except ValueError:
                    pass
        
        return response
    
    @staticmethod
    def parse_header_value(header_value: str) -> Dict[str, str]:
        """Parse a header value with parameters (e.g., From: user@host;tag=abc)."""
        result = {}
        
        # Split by semicolon
        parts = header_value.split(';')
        if parts:
            # First part is the main value
            result['value'] = parts[0].strip()
            
            # Parse parameters
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    result[key.strip()] = value.strip().strip('"')
        
        return result
    
    @staticmethod
    def extract_tag(header_value: str) -> Optional[str]:
        """Extract tag from a header value."""
        parsed = SIPParser.parse_header_value(header_value)
        return parsed.get('tag')

