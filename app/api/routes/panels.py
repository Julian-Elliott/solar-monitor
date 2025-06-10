"""
Panel management API routes
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from uuid import UUID

from app.models import Panel, PanelCreate, PanelUpdate, PanelSummary, APIResponse, PaginatedResponse
from app.services import PanelService
from app.core.database import get_database, Database

router = APIRouter()

async def get_panel_service(db: Database = Depends(get_database)) -> PanelService:
    """Dependency to get panel service"""
    return PanelService(db)

@router.post("/", response_model=APIResponse, status_code=201)
async def create_panel(
    panel_data: PanelCreate,
    service: PanelService = Depends(get_panel_service)
):
    """Create a new solar panel"""
    try:
        panel = await service.create_panel(panel_data)
        return APIResponse(
            success=True,
            message=f"Panel '{panel.name}' created successfully",
            data=panel
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create panel: {str(e)}")

@router.get("/", response_model=PaginatedResponse)
async def get_panels(
    skip: int = Query(0, ge=0, description="Number of panels to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of panels to return"),
    active_only: bool = Query(True, description="Only return active panels"),
    service: PanelService = Depends(get_panel_service)
):
    """Get all panels with pagination"""
    try:
        panels = await service.get_panels(skip=skip, limit=limit, active_only=active_only)
        total = await service.get_panels_count(active_only=active_only)
        
        return PaginatedResponse(
            items=panels,
            total=total,
            page=(skip // limit) + 1,
            size=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve panels: {str(e)}")

@router.get("/{panel_id}", response_model=APIResponse)
async def get_panel(
    panel_id: UUID,
    service: PanelService = Depends(get_panel_service)
):
    """Get a specific panel by ID"""
    panel = await service.get_panel(panel_id)
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found")
    
    return APIResponse(
        success=True,
        message="Panel retrieved successfully",
        data=panel
    )

@router.put("/{panel_id}", response_model=APIResponse)
async def update_panel(
    panel_id: UUID,
    panel_data: PanelUpdate,
    service: PanelService = Depends(get_panel_service)
):
    """Update a panel"""
    panel = await service.update_panel(panel_id, panel_data)
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found")
    
    return APIResponse(
        success=True,
        message="Panel updated successfully",
        data=panel
    )

@router.delete("/{panel_id}", response_model=APIResponse)
async def delete_panel(
    panel_id: UUID,
    service: PanelService = Depends(get_panel_service)
):
    """Delete (deactivate) a panel"""
    success = await service.delete_panel(panel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Panel not found")
    
    return APIResponse(
        success=True,
        message="Panel deleted successfully"
    )

@router.get("/{panel_id}/summary", response_model=APIResponse)
async def get_panel_summary(
    panel_id: UUID,
    service: PanelService = Depends(get_panel_service)
):
    """Get comprehensive panel summary with latest statistics"""
    summary = await service.get_panel_summary(panel_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Panel not found")
    
    return APIResponse(
        success=True,
        message="Panel summary retrieved successfully",
        data=summary
    )
