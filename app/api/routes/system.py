"""
System management API routes
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
import psutil
import asyncio
import logging

from app.models import SystemStatus, APIResponse
from app.services import PanelService, MonitoringService, AlertService, sensor_integration
from app.core.database import get_database, Database
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_services(db: Database = Depends(get_database)):
    """Dependency to get all services"""
    return {
        "panels": PanelService(db),
        "monitoring": MonitoringService(db),
        "alerts": AlertService(db)
    }

@router.get("/health", response_model=APIResponse)
async def health_check(
    services: dict = Depends(get_services)
):
    """Comprehensive health check endpoint"""
    try:
        # Test database connection
        async with services["panels"].db.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Get basic system info
        uptime_seconds = (datetime.utcnow() - datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "service": settings.api_title,
            "version": settings.api_version,
            "database": {
                "status": "connected",
                "type": "TimescaleDB"
            },
            "uptime": uptime_str,
            "system": {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }
        }
        
        return APIResponse(
            success=True,
            message="System is healthy",
            data=health_data
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"System unhealthy: {str(e)}")

@router.get("/status", response_model=APIResponse)
async def get_system_status(
    services: dict = Depends(get_services)
):
    """Get comprehensive system status"""
    try:
        # Get panel statistics
        total_panels = await services["panels"].get_panels_count(active_only=False)
        active_panels = await services["panels"].get_panels_count(active_only=True)
        
        # Get monitoring statistics
        monitoring_stats = await services["monitoring"].get_system_statistics()
        
        # Get alert statistics
        alert_stats = await services["alerts"].get_alert_statistics(hours=24)
        
        # Calculate uptime (simplified)
        uptime = str(timedelta(hours=24))  # Placeholder
        
        status = SystemStatus(
            total_panels=total_panels,
            active_panels=active_panels,
            total_power=monitoring_stats["current_power"],
            system_efficiency=monitoring_stats["system_efficiency"],
            alerts_count=alert_stats["active_alerts"],
            last_update=monitoring_stats["last_update"],
            uptime=uptime
        )
        
        return APIResponse(
            success=True,
            message="System status retrieved successfully",
            data=status
        )
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@router.get("/info", response_model=APIResponse)
async def get_system_info():
    """Get system information and configuration"""
    try:
        info = {
            "api": {
                "title": settings.api_title,
                "version": settings.api_version,
                "description": settings.api_description,
                "debug": settings.debug
            },
            "monitoring": {
                "scan_interval": settings.scan_interval,
                "max_panels": settings.max_panels
            },
            "database": {
                "host": settings.timescale_host,
                "port": settings.timescale_port,
                "database": settings.timescale_database,
                "type": "TimescaleDB"
            },
            "system": {
                "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
                "platform": psutil.os.name,
                "boot_time": datetime.fromtimestamp(psutil.boot_time()),
                "cpu_count": psutil.cpu_count(),
                "memory_total": f"{psutil.virtual_memory().total // (1024**3)}GB"
            }
        }
        
        return APIResponse(
            success=True,
            message="System information retrieved successfully",
            data=info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}")

@router.post("/database/maintenance", response_model=APIResponse)
async def run_database_maintenance(
    services: dict = Depends(get_services)
):
    """Run database maintenance tasks"""
    try:
        async with services["panels"].db.pool.acquire() as conn:
            # Clean up old readings (older than 30 days)
            deleted_count = await conn.fetchval("""
                DELETE FROM readings 
                WHERE timestamp < NOW() - INTERVAL '30 days'
                RETURNING COUNT(*)
            """)
            
            # Clean up resolved alerts (older than 7 days)
            alerts_deleted = await conn.fetchval("""
                DELETE FROM alerts 
                WHERE is_active = FALSE 
                AND resolved_at < NOW() - INTERVAL '7 days'
                RETURNING COUNT(*)
            """)
            
            # Update table statistics
            await conn.execute("ANALYZE readings")
            await conn.execute("ANALYZE panels")
            await conn.execute("ANALYZE alerts")
            
        return APIResponse(
            success=True,
            message="Database maintenance completed successfully",
            data={
                "readings_deleted": deleted_count or 0,
                "alerts_deleted": alerts_deleted or 0,
                "maintenance_time": datetime.utcnow()
            }
        )
    except Exception as e:
        logger.error(f"Database maintenance failed: {e}")
        raise HTTPException(status_code=500, detail=f"Maintenance failed: {str(e)}")

@router.get("/logs", response_model=APIResponse)
async def get_system_logs(
    lines: int = 100
):
    """Get recent system logs (limited for security)"""
    try:
        # This is a simplified implementation
        # In production, you'd want proper log management
        logs = [
            {
                "timestamp": datetime.utcnow(),
                "level": "INFO",
                "message": "API endpoint accessed",
                "source": "system.logs"
            }
        ]
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(logs)} log entries",
            data=logs
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@router.post("/monitoring/start", response_model=APIResponse)
async def start_monitoring():
    """Start sensor monitoring"""
    try:
        if sensor_integration.is_running:
            return APIResponse(
                success=False,
                message="Monitoring is already running"
            )
        
        # Auto-discover panels if needed
        panel_count = await sensor_integration.auto_discover_panels()
        
        # Start monitoring in background
        asyncio.create_task(sensor_integration.start_monitoring(interval=settings.scan_interval))
        
        return APIResponse(
            success=True,
            message=f"Monitoring started for {panel_count} panels",
            data={"panels_registered": panel_count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")

@router.post("/monitoring/stop", response_model=APIResponse)
async def stop_monitoring():
    """Stop sensor monitoring"""
    try:
        sensor_integration.stop_monitoring()
        
        return APIResponse(
            success=True,
            message="Monitoring stopped successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")

@router.get("/monitoring/status", response_model=APIResponse)
async def get_monitoring_status():
    """Get monitoring status"""
    try:
        status = {
            "is_running": sensor_integration.is_running,
            "registered_sensors": len(sensor_integration.sensors),
            "sensor_panels": list(str(panel_id) for panel_id in sensor_integration.sensors.keys())
        }
        
        return APIResponse(
            success=True,
            message="Monitoring status retrieved successfully",
            data=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {str(e)}")
