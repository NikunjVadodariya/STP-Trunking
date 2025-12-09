"""
Database Models
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """User model for SaaS application."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    sip_accounts = relationship("SIPAccount", back_populates="user", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="user", cascade="all, delete-orphan")


class SIPAccount(Base):
    """SIP Account configuration for a user."""
    __tablename__ = "sip_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_name = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)  # Should be encrypted in production
    server_host = Column(String, nullable=False)
    server_port = Column(Integer, default=5060)
    domain = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sip_accounts")
    calls = relationship("Call", back_populates="sip_account")


class Call(Base):
    """Active call tracking."""
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sip_account_id = Column(Integer, ForeignKey("sip_accounts.id"), nullable=False)
    call_id = Column(String, unique=True, index=True, nullable=False)
    from_uri = Column(String, nullable=False)
    to_uri = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # "inbound" or "outbound"
    state = Column(String, nullable=False, default="INITIATING")
    started_at = Column(DateTime, server_default=func.now())
    connected_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # Duration in seconds
    
    # SIP details
    local_tag = Column(String, nullable=True)
    remote_tag = Column(String, nullable=True)
    local_sdp = Column(Text, nullable=True)
    remote_sdp = Column(Text, nullable=True)
    
    # RTP details
    local_rtp_ip = Column(String, nullable=True)
    local_rtp_port = Column(Integer, nullable=True)
    remote_rtp_ip = Column(String, nullable=True)
    remote_rtp_port = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="calls")
    sip_account = relationship("SIPAccount", back_populates="calls")
    records = relationship("CallRecord", back_populates="call", cascade="all, delete-orphan")


class CallRecord(Base):
    """Call record/log for history and analytics."""
    __tablename__ = "call_records"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False)
    event_type = Column(String, nullable=False)  # "INVITE", "RINGING", "CONNECTED", "BYE", etc.
    event_data = Column(Text, nullable=True)  # JSON string with event details
    timestamp = Column(DateTime, server_default=func.now())
    
    # Relationships
    call = relationship("Call", back_populates="records")

