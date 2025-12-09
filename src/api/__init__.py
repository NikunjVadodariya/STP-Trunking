"""
REST API for SIP Trunking SaaS
"""

from .main import app
from .routes import auth, calls, accounts, websocket

__all__ = ['app']

