"""
Alerts API routes
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from uuid import UUID

from app.models import Alert, AlertCreate, APIResponse, PaginatedResponse
from app.services import AlertService
from app.core.database import get_database, Database

router = APIRouter()

async def get_alert_service(db: Database = Depends(get_database)) -> AlertService:
    """Dependency to get alert service"""
    return AlertService(db)

@router.post("/", response_model=APIResponse, status_code=201)
async def create_alert(
    alert_data: AlertCreate,
    service: AlertService = Depends(get_alert_service)
):
    """Create a new alert"""
    try:
        alert = await service.create_alert(alert_data)
        return APIResponse(
            success=True,
            message="Alert created successfully",
            data=alert
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create alert: {str(e)}")

@router.get("/", response_model=PaginatedResponse)
async def get_alerts(
    skip: int = Query(0, ge=0, description="Number of alerts to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of alerts to return"),
    active_only: bool = Query(True, description="Only return active alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity (info|warning|error|critical)"),
    hours: Optional[int] = Query(None, ge=1, le=168, description="Filter by hours from now"),
    service: AlertService = Depends(get_alert_service)
):
    """Get alerts with optional filtering"""
    try:
        alerts = await service.get_alerts(
            active_only=active_only,
            severity=severity,
            limit=limit + skip,  # Get more to handle skip
            hours=hours
        )
        
        # Manual pagination since we're doing complex filtering
        total = len(alerts)
        paginated_alerts = alerts[skip:skip + limit]
        
        return PaginatedResponse(
            items=paginated_alerts,
            total=total,
            page=(skip // limit) + 1,
            size=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")

@router.get("/{alert_id}", response_model=APIResponse)
async def get_alert(
    alert_id: UUID,
    service: AlertService = Depends(get_alert_service)
):
    """Get a specific alert by ID"""
    alert = await service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return APIResponse(
        success=True,
        message="Alert retrieved successfully",
        data=alert
    )

@router.patch("/{alert_id}/resolve", response_model=APIResponse)
async def resolve_alert(
    alert_id: UUID,
    service: AlertService = Depends(get_alert_service)
):
    """Mark an alert as resolved"""
    success = await service.resolve_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found or already resolved")
    
    return APIResponse(
        success=True,
        message="Alert resolved successfully"
    )

@router.get("/panels/{panel_id}", response_model=PaginatedResponse)
async def get_panel_alerts(
    panel_id: UUID,
    active_only: bool = Query(True, description="Only return active alerts"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of alerts to return"),
    service: AlertService = Depends(get_alert_service)
):
    """Get alerts for a specific panel"""
    try:
        alerts = await service.get_panel_alerts(panel_id, active_only=active_only, limit=limit)
        
        return PaginatedResponse(
            items=alerts,
            total=len(alerts),
            page=1,
            size=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve panel alerts: {str(e)}")

@router.patch("/panels/{panel_id}/resolve", response_model=APIResponse)
async def resolve_panel_alerts(
    panel_id: UUID,
    alert_type: Optional[str] = Query(None, description="Specific alert type to resolve"),
    service: AlertService = Depends(get_alert_service)
):
    """Resolve all alerts for a panel"""
    try:
        count = await service.resolve_panel_alerts(panel_id, alert_type=alert_type)
        
        return APIResponse(
            success=True,
            message=f"Resolved {count} alert(s) for panel",
            data={"resolved_count": count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve panel alerts: {str(e)}")

@router.get("/statistics/summary", response_model=APIResponse)
async def get_alert_statistics(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    service: AlertService = Depends(get_alert_service)
):
    """Get alert statistics for the specified time period"""
    try:
        stats = await service.get_alert_statistics(hours=hours)
        return APIResponse(
            success=True,
            message="Alert statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert statistics: {str(e)}")
