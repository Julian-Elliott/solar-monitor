"""
Panel management service
Handles CRUD operations for solar panels
"""

import asyncpg
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from app.models import Panel, PanelCreate, PanelUpdate, PanelSummary
from app.core.database import Database

logger = logging.getLogger(__name__)

class PanelService:
    """Service for managing solar panels"""
    
    def __init__(self, database: Database):
        self.db = database
    
    async def create_panel(self, panel_data: PanelCreate) -> Panel:
        """Create a new panel"""
        panel_id = uuid4()
        now = datetime.utcnow()
        
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO panels (id, name, model, rated_power, i2c_address, location, 
                                  installation_date, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING *
            """, panel_id, panel_data.name, panel_data.model, panel_data.rated_power,
                panel_data.i2c_address, panel_data.location, now, now, now)
            
            logger.info(f"✅ Created panel: {panel_data.name} (ID: {panel_id})")
            return Panel(**dict(row))
    
    async def get_panel(self, panel_id: UUID) -> Optional[Panel]:
        """Get a panel by ID"""
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM panels WHERE id = $1", panel_id)
            return Panel(**dict(row)) if row else None
    
    async def get_panels(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[Panel]:
        """Get all panels with pagination"""
        query = "SELECT * FROM panels"
        params = []
        
        if active_only:
            query += " WHERE is_active = TRUE"
        
        query += " ORDER BY created_at DESC LIMIT $1 OFFSET $2"
        params.extend([limit, skip])
        
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [Panel(**dict(row)) for row in rows]
    
    async def update_panel(self, panel_id: UUID, panel_data: PanelUpdate) -> Optional[Panel]:
        """Update a panel"""
        # Build dynamic update query
        updates = []
        params = []
        param_count = 1
        
        for field, value in panel_data.dict(exclude_unset=True).items():
            if value is not None:
                updates.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1
        
        if not updates:
            return await self.get_panel(panel_id)
        
        # Add updated_at
        updates.append(f"updated_at = ${param_count}")
        params.append(datetime.utcnow())
        param_count += 1
        
        # Add panel_id for WHERE clause
        params.append(panel_id)
        
        query = f"""
            UPDATE panels 
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING *
        """
        
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            if row:
                logger.info(f"✅ Updated panel {panel_id}")
                return Panel(**dict(row))
            return None
    
    async def delete_panel(self, panel_id: UUID) -> bool:
        """Soft delete a panel (set inactive)"""
        async with self.db.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE panels 
                SET is_active = FALSE, updated_at = $1
                WHERE id = $2
            """, datetime.utcnow(), panel_id)
            
            success = result.split()[-1] == "1"
            if success:
                logger.info(f"✅ Deleted panel {panel_id}")
            return success
    
    async def get_panel_summary(self, panel_id: UUID) -> Optional[PanelSummary]:
        """Get comprehensive panel summary with latest stats"""
        async with self.db.pool.acquire() as conn:
            # Get panel info
            panel_row = await conn.fetchrow("SELECT * FROM panels WHERE id = $1", panel_id)
            if not panel_row:
                return None
            
            # Get latest reading
            latest_reading_row = await conn.fetchrow("""
                SELECT * FROM readings 
                WHERE panel_id = $1 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, panel_id)
            
            # Get daily stats (today)
            daily_stats = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(power * EXTRACT(EPOCH FROM (LEAD(timestamp, 1, NOW()) OVER (ORDER BY timestamp) - timestamp)) / 3600), 0) as daily_energy,
                    COALESCE(MAX(power), 0) as daily_peak_power,
                    COALESCE(AVG(efficiency), 0) as average_efficiency,
                    COUNT(*) as total_readings
                FROM readings 
                WHERE panel_id = $1 
                AND timestamp >= CURRENT_DATE
                AND timestamp < CURRENT_DATE + INTERVAL '1 day'
            """, panel_id)
            
            # Determine status
            status = "offline"
            if latest_reading_row:
                time_diff = datetime.utcnow() - latest_reading_row['timestamp']
                if time_diff.total_seconds() < 300:  # 5 minutes
                    status = "online"
                elif time_diff.total_seconds() < 3600:  # 1 hour
                    status = "warning"
            
            from app.models import Reading
            latest_reading = Reading(**dict(latest_reading_row)) if latest_reading_row else None
            
            return PanelSummary(
                panel_id=panel_id,
                panel_name=panel_row['name'],
                latest_reading=latest_reading,
                daily_energy=float(daily_stats['daily_energy'] or 0),
                daily_peak_power=float(daily_stats['daily_peak_power'] or 0),
                average_efficiency=float(daily_stats['average_efficiency'] or 0),
                total_readings=int(daily_stats['total_readings'] or 0),
                status=status
            )
    
    async def get_panels_count(self, active_only: bool = True) -> int:
        """Get total count of panels"""
        query = "SELECT COUNT(*) FROM panels"
        if active_only:
            query += " WHERE is_active = TRUE"
        
        async with self.db.pool.acquire() as conn:
            return await conn.fetchval(query)
