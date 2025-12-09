"""
WebSocket Routes for Real-time Updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List
import json
import logging

from ...services.websocket_manager import WebSocketManager

router = APIRouter()
logger = logging.getLogger(__name__)

# WebSocket manager instance
ws_manager = WebSocketManager()


@router.websocket("/calls")
async def websocket_calls(websocket: WebSocket):
    """WebSocket endpoint for real-time call updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Handle client messages if needed
                logger.info(f"Received WebSocket message: {message}")
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


@router.websocket("/calls/{call_id}")
async def websocket_call_detail(websocket: WebSocket, call_id: str):
    """WebSocket endpoint for specific call updates."""
    await ws_manager.connect(websocket, call_id=call_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.info(f"Received WebSocket message for call {call_id}: {message}")
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, call_id=call_id)
        logger.info(f"WebSocket client disconnected for call {call_id}")

