"""
Alert management service
Handles alert creation, retrieval, and resolution
"""

import logging
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from app.models import Alert, AlertCreate
from app.core.database import Database

logger = logging.getLogger(__name__)

class AlertService:
    """Service for managing system alerts"""
    
    def __init__(self, database: Database):
        self.db = database
    
    async def create_alert(self, alert_data: AlertCreate) -> Alert:
        """Create a new alert"""
        alert_id = uuid4()
        now = datetime.utcnow()
        
        async with self.db.pool.acquire() as conn:
            # First ensure alerts table exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    panel_id UUID REFERENCES panels(id) ON DELETE CASCADE,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'critical')),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    resolved_at TIMESTAMPTZ NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Create index if not exists
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_panel_id ON alerts(panel_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC)")
            
            row = await conn.fetchrow("""
                INSERT INTO alerts (id, panel_id, alert_type, message, severity, created_at, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
            """, alert_id, alert_data.panel_id, alert_data.alert_type, 
                alert_data.message, alert_data.severity, now, True)
            
            logger.info(f"🚨 Created {alert_data.severity} alert for panel {alert_data.panel_id}: {alert_data.message}")
            return Alert(**dict(row))
    
    async def get_alert(self, alert_id: UUID) -> Optional[Alert]:
        """Get an alert by ID"""
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM alerts WHERE id = $1", alert_id)
            return Alert(**dict(row)) if row else None
    
    async def get_panel_alerts(self, panel_id: UUID, active_only: bool = True, 
                              limit: int = 100) -> List[Alert]:
        """Get alerts for a specific panel"""
        query = "SELECT * FROM alerts WHERE panel_id = $1"
        params = [panel_id]
        
        if active_only:
            query += " AND is_active = TRUE"
        
        query += " ORDER BY created_at DESC LIMIT $2"
        params.append(limit)
        
        async with self.db.pool.acquire() as conn:
            try:
                rows = await conn.fetch(query, *params)
                return [Alert(**dict(row)) for row in rows]
            except Exception as e:
                # Table might not exist yet
                logger.warning(f"Could not fetch alerts: {e}")
                return []
    
    async def get_alerts(self, active_only: bool = True, severity: Optional[str] = None,
                        limit: int = 100, hours: Optional[int] = None) -> List[Alert]:
        """Get system alerts with filters"""
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        param_count = 1
        
        if active_only:
            query += " AND is_active = TRUE"
        
        if severity:
            query += f" AND severity = ${param_count}"
            params.append(severity)
            param_count += 1
        
        if hours:
            query += f" AND created_at >= ${param_count}"
            params.append(datetime.utcnow() - timedelta(hours=hours))
            param_count += 1
        
        query += f" ORDER BY created_at DESC LIMIT ${param_count}"
        params.append(limit)
        
        async with self.db.pool.acquire() as conn:
            try:
                rows = await conn.fetch(query, *params)
                return [Alert(**dict(row)) for row in rows]
            except Exception as e:
                # Table might not exist yet
                logger.warning(f"Could not fetch alerts: {e}")
                return []
    
    async def resolve_alert(self, alert_id: UUID) -> bool:
        """Mark an alert as resolved"""
        async with self.db.pool.acquire() as conn:
            try:
                result = await conn.execute("""
                    UPDATE alerts 
                    SET is_active = FALSE, resolved_at = $1
                    WHERE id = $2 AND is_active = TRUE
                """, datetime.utcnow(), alert_id)
                
                success = result.split()[-1] == "1"
                if success:
                    logger.info(f"✅ Resolved alert {alert_id}")
                return success
            except Exception as e:
                logger.error(f"Failed to resolve alert {alert_id}: {e}")
                return False
    
    async def resolve_panel_alerts(self, panel_id: UUID, alert_type: Optional[str] = None) -> int:
        """Resolve all alerts for a panel, optionally filtered by type"""
        query = """
            UPDATE alerts 
            SET is_active = FALSE, resolved_at = $1
            WHERE panel_id = $2 AND is_active = TRUE
        """
        params = [datetime.utcnow(), panel_id]
        
        if alert_type:
            query += " AND alert_type = $3"
            params.append(alert_type)
        
        async with self.db.pool.acquire() as conn:
            try:
                result = await conn.execute(query, *params)
                count = int(result.split()[-1])
                if count > 0:
                    logger.info(f"✅ Resolved {count} alerts for panel {panel_id}")
                return count
            except Exception as e:
                logger.error(f"Failed to resolve panel alerts: {e}")
                return 0
    
    async def get_alert_statistics(self, hours: int = 24) -> dict:
        """Get alert statistics for the specified time period"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with self.db.pool.acquire() as conn:
            try:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_alerts,
                        COUNT(*) FILTER (WHERE is_active = TRUE) as active_alerts,
                        COUNT(*) FILTER (WHERE severity = 'critical') as critical_alerts,
                        COUNT(*) FILTER (WHERE severity = 'error') as error_alerts,
                        COUNT(*) FILTER (WHERE severity = 'warning') as warning_alerts,
                        COUNT(*) FILTER (WHERE severity = 'info') as info_alerts,
                        COUNT(*) FILTER (WHERE resolved_at IS NOT NULL) as resolved_alerts
                    FROM alerts 
                    WHERE created_at >= $1
                """, start_time)
                
                return {
                    "period_hours": hours,
                    "total_alerts": int(stats['total_alerts'] or 0),
                    "active_alerts": int(stats['active_alerts'] or 0),
                    "critical_alerts": int(stats['critical_alerts'] or 0),
                    "error_alerts": int(stats['error_alerts'] or 0),
                    "warning_alerts": int(stats['warning_alerts'] or 0),
                    "info_alerts": int(stats['info_alerts'] or 0),
                    "resolved_alerts": int(stats['resolved_alerts'] or 0)
                }
            except Exception as e:
                logger.warning(f"Could not get alert statistics: {e}")
                return {
                    "period_hours": hours,
                    "total_alerts": 0,
                    "active_alerts": 0,
                    "critical_alerts": 0,
                    "error_alerts": 0,
                    "warning_alerts": 0,
                    "info_alerts": 0,
                    "resolved_alerts": 0
                }
