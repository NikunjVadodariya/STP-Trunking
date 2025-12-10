"""
Call Service - Business logic for call management
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import logging
import asyncio
import socket

from ..database.models import Call, CallRecord, SIPAccount
from ..client.sip_client import SIPClient
from ..protocol.sip_utils import generate_call_id, build_sip_uri

logger = logging.getLogger(__name__)


class CallService:
    """Service for managing SIP calls."""
    
    # Class-level storage for call state updates (shared across instances)
    _call_state_updates = {}  # call_id -> (state, kwargs)
    _db_session_factory = None
    
    def __init__(self, db: Session):
        self.db = db
        self.active_clients: dict = {}  # sip_account_id -> SIPClient
        # Store session factory for callbacks
        if CallService._db_session_factory is None:
            from ..database.database import SessionLocal
            CallService._db_session_factory = SessionLocal
    
    async def initiate_call(
        self,
        user_id: int,
        sip_account_id: int,
        to_uri: str
    ) -> Call:
        """Initiate a new call."""
        # Get SIP account
        sip_account = self.db.query(SIPAccount).filter(
            SIPAccount.id == sip_account_id
        ).first()
        if not sip_account:
            raise ValueError("SIP account not found")
        
        # Get or create SIP client for this account
        client = self._get_or_create_client(sip_account)
        
        # Generate call ID
        call_id = generate_call_id()
        
        # Build from URI
        from_uri = build_sip_uri(user=sip_account.username, host=sip_account.domain)
        print(f"From URI: {from_uri}")
        
        # Create call record
        call = Call(
            user_id=user_id,
            sip_account_id=sip_account_id,
            call_id=call_id,
            from_uri=from_uri,
            to_uri=to_uri,
            direction="outbound",
            state="INITIATING"
        )
        self.db.add(call)
        
        # Commit call first to get the ID
        self.db.commit()
        self.db.refresh(call)
        
        # Create call record after call is committed
        record = CallRecord(
            call_id=call.id,
            event_type="INVITE",
            event_data=f'{{"to_uri": "{to_uri}"}}'
        )
        self.db.add(record)
        self.db.commit()
        
        # Initiate call via SIP client
        try:
            client.make_call(to_uri)
            logger.info(f"Call initiated: {call_id}")
        except socket.gaierror as e:
            error_msg = f"Cannot resolve hostname '{sip_account.server_host}'. Please check the SIP server hostname/IP address."
            logger.error(f"Error initiating call: {error_msg}")
            call.state = "FAILED"
            self.db.commit()
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Error initiating call: {str(e)}"
            logger.error(error_msg)
            call.state = "FAILED"
            self.db.commit()
            raise ValueError(error_msg) from e
        
        return call
    
    async def hangup_call(self, call_id: str):
        """Hang up a call."""
        call = self.db.query(Call).filter(Call.call_id == call_id).first()
        if not call:
            raise ValueError("Call not found")
        
        # Get SIP client
        client = self._get_or_create_client(call.sip_account)
        
        # Hangup
        try:
            client.hangup(call_id)
            call.state = "TERMINATED"
            call.ended_at = datetime.utcnow()
            if call.connected_at:
                call.duration = (call.ended_at - call.connected_at).total_seconds()
            
            # Create call record
            record = CallRecord(
                call_id=call.id,
                event_type="BYE",
                event_data='{"action": "hangup"}'
            )
            self.db.add(record)
            self.db.commit()
            
            logger.info(f"Call {call_id} terminated")
        except Exception as e:
            logger.error(f"Error hanging up call: {e}")
            raise
    
    def _update_call_state_sync(
        self,
        call_id: str,
        state: str,
        **kwargs
    ):
        """Update call state synchronously (for use in callbacks)."""
        # Create a new database session for thread safety
        if CallService._db_session_factory is None:
            logger.error("Database session factory not initialized")
            return
        
        db = CallService._db_session_factory()
        try:
            call = db.query(Call).filter(Call.call_id == call_id).first()
            if not call:
                logger.warning(f"Call {call_id} not found in database")
                return
            
            call.state = state
            
            if state == "CONNECTED" and not call.connected_at:
                call.connected_at = datetime.utcnow()
            elif state == "TERMINATED" and not call.ended_at:
                call.ended_at = datetime.utcnow()
                if call.connected_at:
                    call.duration = (call.ended_at - call.connected_at).total_seconds()
            
            # Update other fields from kwargs
            for key, value in kwargs.items():
                if hasattr(call, key):
                    setattr(call, key, value)
            
            # Create call record
            record = CallRecord(
                call_id=call.id,
                event_type=state,
                event_data=str(kwargs)
            )
            db.add(record)
            db.commit()
            logger.info(f"Call {call_id} state updated to {state}")
        except Exception as e:
            logger.error(f"Error updating call state: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    
    async def update_call_state(
        self,
        call_id: str,
        state: str,
        **kwargs
    ):
        """Update call state (async version for API use)."""
        self._update_call_state_sync(call_id, state, **kwargs)
    
    def _get_or_create_client(self, sip_account: SIPAccount) -> SIPClient:
        """Get or create SIP client for account."""
        if sip_account.id in self.active_clients:
            return self.active_clients[sip_account.id]
        
        # Create client configuration
        import tempfile
        import yaml
        from pathlib import Path
        
        config = {
            'client': {
                'server_host': sip_account.server_host,
                'server_port': sip_account.server_port,
                'username': sip_account.username,
                'password': sip_account.password,
                'domain': sip_account.domain,
                'local_ip': '0.0.0.0',
                'local_port': 0
            }
        }
        
        # Create temporary config file
        config_file = Path(tempfile.gettempdir()) / f"sip_client_{sip_account.id}.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Create and start client
        client = SIPClient(config_path=str(config_file))
        client.start()
        
        # Register client
        client.register()
        
        # Set up callbacks - use thread-safe database updates
        def on_connected(cid):
            logger.info(f"Callback: Call {cid} connected")
            self._update_call_state_sync(cid, "CONNECTED")
        
        def on_ended(cid):
            logger.info(f"Callback: Call {cid} ended")
            self._update_call_state_sync(cid, "TERMINATED")
        
        # Also handle intermediate states
        def on_ringing(cid):
            logger.info(f"Callback: Call {cid} ringing")
            self._update_call_state_sync(cid, "RINGING")
        
        def on_trying(cid):
            logger.info(f"Callback: Call {cid} trying")
            self._update_call_state_sync(cid, "TRYING")
        
        client.set_on_call_connected(on_connected)
        client.set_on_call_ended(on_ended)
        client.set_on_call_ringing(on_ringing)
        client.set_on_call_trying(on_trying)
        
        self.active_clients[sip_account.id] = client
        return client

