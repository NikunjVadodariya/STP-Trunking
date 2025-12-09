"""
SIP Utility Functions
"""

import random
import string
import hashlib
import time


def generate_tag(length=10):
    """Generate a random tag for SIP messages."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_branch():
    """Generate a branch ID for Via header."""
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    timestamp = str(int(time.time() * 1000))
    return f"z9hG4bK{random_str}{timestamp}"


def generate_call_id():
    """Generate a unique Call-ID."""
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    timestamp = str(int(time.time() * 1000))
    return f"{random_str}-{timestamp}@localhost"


def calculate_response_delay(rtt=0):
    """Calculate response delay based on RTT."""
    return max(0, rtt / 2)


def parse_sip_uri(uri):
    """Parse a SIP URI into components."""
    if not uri.startswith('sip:') and not uri.startswith('sips:'):
        return None
    
    scheme = 'sip' if uri.startswith('sip:') else 'sips'
    uri_part = uri[4:] if scheme == 'sip' else uri[5:]
    
    # Parse user@host:port
    if '@' in uri_part:
        user_part, host_part = uri_part.split('@', 1)
    else:
        user_part = None
        host_part = uri_part
    
    # Parse host:port
    if ':' in host_part:
        host, port = host_part.split(':', 1)
        port = int(port)
    else:
        host = host_part
        port = 5060 if scheme == 'sip' else 5061
    
    # Parse parameters
    params = {}
    if ';' in host_part:
        parts = host_part.split(';')
        host_part = parts[0]
        for param in parts[1:]:
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
    
    return {
        'scheme': scheme,
        'user': user_part,
        'host': host,
        'port': port,
        'params': params
    }


def build_sip_uri(user=None, host='localhost', port=5060, scheme='sip', params=None):
    """Build a SIP URI from components."""
    uri = f"{scheme}:"
    if user:
        uri += f"{user}@"
    uri += host
    if port != 5060:
        uri += f":{port}"
    
    if params:
        for key, value in params.items():
            uri += f";{key}={value}"
    
    return uri


def generate_authenticate_header(realm, nonce, algorithm='MD5'):
    """Generate WWW-Authenticate header value."""
    return f'Digest realm="{realm}", nonce="{nonce}", algorithm={algorithm}'


def calculate_digest_response(username, realm, password, method, uri, nonce, nc='00000001', cnonce=None, qop=None):
    """Calculate SIP digest authentication response."""
    if cnonce is None:
        cnonce = generate_tag(16)
    
    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    
    if qop:
        response = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()).hexdigest()
    else:
        response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
    
    return response, cnonce

