"""WebSocket API for Real-time Updates"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """
    WebSocket endpoint for real-time metrics updates
    
    Sends periodic updates with:
    - Current request rate
    - Latest metrics
    - Alert notifications
    """
    await manager.connect(websocket)
    
    try:
        # Send initial connection message
        await manager.send_personal_message(
            {
                "type": "connected",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to metrics stream"
            },
            websocket
        )
        
        # Keep connection alive and listen for client messages
        while True:
            try:
                # Wait for client message (with timeout)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Process client message if needed
                try:
                    message = json.loads(data)
                    if message.get('type') == 'ping':
                        await manager.send_personal_message(
                            {
                                "type": "pong",
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            websocket
                        )
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await manager.send_personal_message(
                    {
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_metrics_update(data: dict):
    """
    Broadcast metrics update to all connected clients
    
    Args:
        data: Metrics data dictionary
    """
    message = {
        "type": "metrics_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
    await manager.broadcast(message)


async def broadcast_alert(alert: dict):
    """
    Broadcast alert to all connected clients
    
    Args:
        alert: Alert dictionary
    """
    message = {
        "type": "alert",
        "timestamp": datetime.utcnow().isoformat(),
        "data": alert
    }
    await manager.broadcast(message)


async def broadcast_drift_detected(drift_data: dict):
    """
    Broadcast drift detection to all connected clients
    
    Args:
        drift_data: Drift information
    """
    message = {
        "type": "drift_detected",
        "timestamp": datetime.utcnow().isoformat(),
        "data": drift_data
    }
    await manager.broadcast(message)

