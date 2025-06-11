"""
Monitoring service for sensor data collection and analysis
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
import json

from app.models import Reading, ReadingCreate, Alert, AlertCreate
from app.core.database import Database

logger = logging.getLogger(__name__)

class MonitoringService:
    """Service for sensor monitoring and data collection"""
    
    def __init__(self, database: Database):
        self.db = database
        self.is_monitoring = False
    
    async def create_reading(self, reading_data: ReadingCreate) -> Reading:
        """Store a new sensor reading"""
        reading_id = uuid4()
        now = datetime.now(timezone.utc)  # Use timezone-aware UTC datetime
        
        # Convert alerts list to JSON
        alerts_json = json.dumps(reading_data.alerts)
        
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO readings (id, panel_id, timestamp, voltage, current, power, 
                                    temperature, efficiency, conditions, alerts, shunt_voltage, raw_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING *
            """, reading_id, reading_data.panel_id, now, reading_data.voltage,
                reading_data.current, reading_data.power, reading_data.temperature,
                reading_data.efficiency, reading_data.conditions, alerts_json,
                reading_data.shunt_voltage, None)
            
            # Update panel's last reading time
            await conn.execute("""
                UPDATE panels 
                SET updated_at = $1 
                WHERE id = $2
            """, now, reading_data.panel_id)
            
            logger.debug(f"📊 Stored reading for panel {reading_data.panel_id}: {reading_data.power}W")
            return Reading(**dict(row))
    
    async def get_reading(self, reading_id: UUID) -> Optional[Reading]:
        """Get a reading by ID"""
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM readings WHERE id = $1", reading_id)
            if row:
                # Parse alerts JSON
                alerts = json.loads(row['alerts']) if row['alerts'] else []
                row_dict = dict(row)
                row_dict['alerts'] = alerts
                return Reading(**row_dict)
            return None
    
    async def get_panel_readings(self, panel_id: UUID, limit: int = 100, 
                               hours: Optional[int] = None) -> List[Reading]:
        """Get readings for a specific panel"""
        query = "SELECT * FROM readings WHERE panel_id = $1"
        params = [panel_id]
        
        if hours:
            query += " AND timestamp >= $2"
            params.append(datetime.now(timezone.utc) - timedelta(hours=hours))
        
        query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            readings = []
            for row in rows:
                # Parse alerts JSON
                alerts = json.loads(row['alerts']) if row['alerts'] else []
                row_dict = dict(row)
                row_dict['alerts'] = alerts
                readings.append(Reading(**row_dict))
            return readings
    
    async def get_latest_readings(self, limit: int = 50) -> List[Reading]:
        """Get the latest readings across all panels"""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT ON (panel_id) *
                FROM readings
                ORDER BY panel_id, timestamp DESC
                LIMIT $1
            """, limit)
            readings = []
            for row in rows:
                # Parse alerts JSON
                alerts = json.loads(row['alerts']) if row['alerts'] else []
                row_dict = dict(row)
                row_dict['alerts'] = alerts
                readings.append(Reading(**row_dict))
            return readings
    
    async def get_all_recent_readings(self, limit: int = 50, hours: Optional[int] = None) -> List[Reading]:
        """Get all recent readings chronologically (not just latest per panel)"""
        query = "SELECT * FROM readings"
        params = []
        
        if hours:
            query += " WHERE timestamp >= $1"
            params.append(datetime.now(timezone.utc) - timedelta(hours=hours))
        
        query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            readings = []
            for row in rows:
                # Parse alerts JSON
                alerts = json.loads(row['alerts']) if row['alerts'] else []
                row_dict = dict(row)
                row_dict['alerts'] = alerts
                readings.append(Reading(**row_dict))
            return readings
    
    async def analyze_reading(self, reading: ReadingCreate) -> List[str]:
        """Analyze a reading and generate alerts"""
        alerts = []
        
        # Voltage checks
        if reading.voltage < 5.0:
            alerts.append("Low voltage detected")
        elif reading.voltage > 25.0:
            alerts.append("High voltage detected")
        
        # Current checks
        if reading.current < 0.1 and reading.voltage > 10.0:
            alerts.append("Low current output")
        elif reading.current > 15.0:
            alerts.append("High current detected")
        
        # Power checks
        if reading.power < 10.0 and reading.voltage > 15.0:
            alerts.append("Low power generation")
        elif reading.power > 120.0:  # Above rated capacity
            alerts.append("Power output exceeding rated capacity")
        
        # Efficiency checks
        if reading.efficiency < 50.0:
            alerts.append("Low efficiency detected")
        
        # Temperature checks (if available)
        if reading.temperature:
            if reading.temperature > 80.0:
                alerts.append("High temperature warning")
            elif reading.temperature < -10.0:
                alerts.append("Low temperature warning")
        
        return alerts
    
    async def get_panel_statistics(self, panel_id: UUID, hours: int = 24) -> Dict[str, Any]:
        """Get statistical analysis for a panel"""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        async with self.db.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as reading_count,
                    AVG(voltage) as avg_voltage,
                    AVG(current) as avg_current,
                    AVG(power) as avg_power,
                    MAX(power) as max_power,
                    MIN(power) as min_power,
                    AVG(efficiency) as avg_efficiency,
                    MAX(efficiency) as max_efficiency,
                    MIN(efficiency) as min_efficiency,
                    AVG(temperature) as avg_temperature,
                    -- Energy calculation (Wh) - approximation using average power
                    SUM(power * EXTRACT(EPOCH FROM (LEAD(timestamp, 1, NOW()) OVER (ORDER BY timestamp) - timestamp)) / 3600) as energy_wh
                FROM readings 
                WHERE panel_id = $1 
                AND timestamp >= $2
                ORDER BY timestamp
            """, panel_id, start_time)
            
            # Count alerts
            alert_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM readings 
                WHERE panel_id = $1 
                AND timestamp >= $2
                AND jsonb_array_length(alerts) > 0
            """, panel_id, start_time)
            
            return {
                "period_hours": hours,
                "reading_count": int(stats['reading_count'] or 0),
                "avg_voltage": float(stats['avg_voltage'] or 0),
                "avg_current": float(stats['avg_current'] or 0),
                "avg_power": float(stats['avg_power'] or 0),
                "max_power": float(stats['max_power'] or 0),
                "min_power": float(stats['min_power'] or 0),
                "avg_efficiency": float(stats['avg_efficiency'] or 0),
                "max_efficiency": float(stats['max_efficiency'] or 0),
                "min_efficiency": float(stats['min_efficiency'] or 0),
                "avg_temperature": float(stats['avg_temperature'] or 0) if stats['avg_temperature'] else None,
                "energy_wh": float(stats['energy_wh'] or 0),
                "alerts_count": int(alert_count or 0)
            }
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        async with self.db.pool.acquire() as conn:
            # Panel counts
            panel_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_panels,
                    COUNT(*) FILTER (WHERE is_active = TRUE) as active_panels
                FROM panels
            """)
            
            # Current system power (latest readings)
            current_power = await conn.fetchval("""
                SELECT COALESCE(SUM(power), 0)
                FROM (
                    SELECT DISTINCT ON (panel_id) power
                    FROM readings
                    WHERE timestamp >= NOW() - INTERVAL '5 minutes'
                    ORDER BY panel_id, timestamp DESC
                ) latest_readings
            """)
            
            # System efficiency (weighted average)
            system_efficiency = await conn.fetchval("""
                SELECT COALESCE(AVG(efficiency), 0)
                FROM (
                    SELECT DISTINCT ON (panel_id) efficiency
                    FROM readings
                    WHERE timestamp >= NOW() - INTERVAL '5 minutes'
                    ORDER BY panel_id, timestamp DESC
                ) latest_readings
            """)
            
            # Active alerts count
            alerts_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM (
                    SELECT DISTINCT ON (panel_id) alerts
                    FROM readings
                    WHERE timestamp >= NOW() - INTERVAL '1 hour'
                    AND jsonb_array_length(alerts) > 0
                    ORDER BY panel_id, timestamp DESC
                ) recent_alerts
            """)
            
            return {
                "total_panels": int(panel_stats['total_panels'] or 0),
                "active_panels": int(panel_stats['active_panels'] or 0),
                "current_power": float(current_power or 0),
                "system_efficiency": float(system_efficiency or 0),
                "alerts_count": int(alerts_count or 0),
                "last_update": datetime.utcnow()
            }
