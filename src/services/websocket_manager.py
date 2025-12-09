"""
WebSocket Manager for Real-time Updates
"""

from fastapi import WebSocket
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.call_connections: Dict[str, List[WebSocket]] = {}  # call_id -> [websockets]
    
    async def connect(self, websocket: WebSocket, call_id: Optional[str] = None):
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if call_id:
            if call_id not in self.call_connections:
                self.call_connections[call_id] = []
            self.call_connections[call_id].append(websocket)
        
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, call_id: Optional[str] = None):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if call_id and call_id in self.call_connections:
            if websocket in self.call_connections[call_id]:
                self.call_connections[call_id].remove(websocket)
            if not self.call_connections[call_id]:
                del self.call_connections[call_id]
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast_call_update(self, call_id: str, data: dict):
        """Broadcast call update to all connected clients."""
        message = json.dumps({
            "type": "call_update",
            "call_id": call_id,
            "data": data
        })
        
        # Send to call-specific connections
        if call_id in self.call_connections:
            disconnected = []
            for connection in self.call_connections[call_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending to WebSocket: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect(conn, call_id)
        
        # Also send to general connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_message(self, message: dict):
        """Broadcast a message to all connected clients."""
        message_str = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

