"""
Readings API routes
"""

from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from uuid import UUID
import json
import asyncio
import logging

from app.models import Reading, ReadingCreate, APIResponse, PaginatedResponse
from app.services import MonitoringService
from app.core.database import get_database, Database

logger = logging.getLogger(__name__)
router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message, default=str)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

manager = ConnectionManager()

async def get_monitoring_service(db: Database = Depends(get_database)) -> MonitoringService:
    """Dependency to get monitoring service"""
    return MonitoringService(db)

@router.post("/", response_model=APIResponse, status_code=201)
async def create_reading(
    reading_data: ReadingCreate,
    service: MonitoringService = Depends(get_monitoring_service)
):
    """Create a new sensor reading"""
    try:
        # Analyze reading for alerts
        alerts = await service.analyze_reading(reading_data)
        reading_data.alerts = alerts
        
        # Store reading
        reading = await service.create_reading(reading_data)
        
        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "new_reading",
            "data": {
                "reading": reading.dict(),
                "alerts": alerts
            }
        })
        
        return APIResponse(
            success=True,
            message="Reading created successfully",
            data=reading
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create reading: {str(e)}")

@router.get("/", response_model=PaginatedResponse)
async def get_readings(
    skip: int = Query(0, ge=0, description="Number of readings to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of readings to return"),
    panel_id: Optional[UUID] = Query(None, description="Filter by panel ID"),
    hours: Optional[int] = Query(None, ge=1, le=168, description="Filter by hours from now"),
    service: MonitoringService = Depends(get_monitoring_service)
):
    """Get readings with optional filtering"""
    try:
        if panel_id:
            readings = await service.get_panel_readings(panel_id, limit=limit, hours=hours)
            total = len(readings)  # Simplified for panel-specific queries
        else:
            readings = await service.get_latest_readings(limit=limit)
            total = len(readings)  # Simplified for latest readings
        
        return PaginatedResponse(
            items=readings,
            total=total,
            page=(skip // limit) + 1,
            size=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve readings: {str(e)}")

@router.get("/{reading_id}", response_model=APIResponse)
async def get_reading(
    reading_id: UUID,
    service: MonitoringService = Depends(get_monitoring_service)
):
    """Get a specific reading by ID"""
    reading = await service.get_reading(reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    
    return APIResponse(
        success=True,
        message="Reading retrieved successfully",
        data=reading
    )

@router.get("/panels/{panel_id}/statistics", response_model=APIResponse)
async def get_panel_statistics(
    panel_id: UUID,
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    service: MonitoringService = Depends(get_monitoring_service)
):
    """Get statistical analysis for a panel"""
    try:
        stats = await service.get_panel_statistics(panel_id, hours=hours)
        return APIResponse(
            success=True,
            message="Panel statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.get("/system/statistics", response_model=APIResponse)
async def get_system_statistics(
    service: MonitoringService = Depends(get_monitoring_service)
):
    """Get overall system statistics"""
    try:
        stats = await service.get_system_statistics()
        return APIResponse(
            success=True,
            message="System statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system statistics: {str(e)}")

@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live data streaming"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Echo back (for connection testing)
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
