#!/usr/bin/env python3
"""
PS100 Solar Monitor Database Schema
Optimized for Anker SOLIX PS100 solar panel monitoring
"""

import sqlite3
import psycopg2
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple
import logging

class PS100Database:
    """Database manager for PS100 solar monitoring system"""
    
    def __init__(self, db_type='sqlite', db_path='ps100_solar.db', pg_config=None):
        """Initialize database connection
        
        Args:
            db_type: 'sqlite' or 'postgresql'
            db_path: Path for SQLite database
            pg_config: PostgreSQL connection config dict
        """
        self.db_type = db_type
        self.db_path = db_path
        self.pg_config = pg_config
        self.connection = None
        
        self.logger = logging.getLogger(__name__)
        self._connect()
        self._create_tables()
        
    def _connect(self):
        """Establish database connection"""
        try:
            if self.db_type == 'sqlite':
                self.connection = sqlite3.connect(
                    self.db_path, 
                    check_same_thread=False,
                    timeout=30.0
                )
                self.connection.row_factory = sqlite3.Row
                # Enable WAL mode for better concurrent access
                self.connection.execute("PRAGMA journal_mode=WAL")
                self.connection.execute("PRAGMA synchronous=NORMAL")
                
            elif self.db_type == 'postgresql':
                if not self.pg_config:
                    raise ValueError("PostgreSQL config required")
                self.connection = psycopg2.connect(**self.pg_config)
                
            self.logger.info(f"✅ Connected to {self.db_type} database")
            
        except Exception as e:
            self.logger.error(f"❌ Database connection failed: {e}")
            raise
            
    def _create_tables(self):
        """Create tables optimized for PS100 monitoring"""
        
        # Panel configuration table
        panels_sql = """
        CREATE TABLE IF NOT EXISTS panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            panel_id TEXT UNIQUE NOT NULL,
            model TEXT DEFAULT 'Anker SOLIX PS100',
            location TEXT,
            sensor_address TEXT,
            rated_power REAL DEFAULT 100.0,
            rated_voltage REAL DEFAULT 26.5,
            rated_current REAL DEFAULT 3.77,
            installation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active BOOLEAN DEFAULT TRUE,
            notes TEXT,
            config_json TEXT
        )"""
        
        # Real-time readings table (raw data)
        readings_sql = """
        CREATE TABLE IF NOT EXISTS panel_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            panel_id TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            voltage REAL NOT NULL,
            current REAL NOT NULL,
            power REAL NOT NULL,
            energy REAL DEFAULT 0,
            temperature REAL,
            shunt_voltage REAL,
            alert_flags TEXT,
            conditions_estimate TEXT,
            FOREIGN KEY (panel_id) REFERENCES panels (panel_id)
        )"""
        
        # Aggregated data table (for performance)
        aggregated_sql = """
        CREATE TABLE IF NOT EXISTS panel_aggregates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            panel_id TEXT NOT NULL,
            period_start TIMESTAMP NOT NULL,
            period_end TIMESTAMP NOT NULL,
            interval_type TEXT NOT NULL, -- '1min', '5min', '1hour', '1day'
            
            -- Voltage statistics
            voltage_min REAL,
            voltage_max REAL,
            voltage_avg REAL,
            
            -- Current statistics  
            current_min REAL,
            current_max REAL,
            current_avg REAL,
            
            -- Power statistics
            power_min REAL,
            power_max REAL,
            power_avg REAL,
            power_peak REAL,
            
            -- Energy totals
            energy_total REAL,
            energy_theoretical REAL,
            efficiency_percent REAL,
            
            -- Environmental
            temperature_min REAL,
            temperature_max REAL,
            temperature_avg REAL,
            
            -- Data quality
            reading_count INTEGER,
            alert_count INTEGER,
            uptime_percent REAL,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(panel_id, period_start, interval_type),
            FOREIGN KEY (panel_id) REFERENCES panels (panel_id)
        )"""
        
        # System-wide aggregates
        system_aggregates_sql = """
        CREATE TABLE IF NOT EXISTS system_aggregates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_start TIMESTAMP NOT NULL,
            period_end TIMESTAMP NOT NULL,
            interval_type TEXT NOT NULL,
            
            -- Total system metrics
            total_power_avg REAL,
            total_power_peak REAL,
            total_energy REAL,
            total_energy_theoretical REAL,
            system_efficiency_percent REAL,
            
            -- Panel statistics
            active_panels INTEGER,
            total_panels INTEGER,
            best_performing_panel TEXT,
            worst_performing_panel TEXT,
            
            -- Alerts and health
            total_alerts INTEGER,
            system_uptime_percent REAL,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(period_start, interval_type)
        )"""
        
        # Performance events table
        events_sql = """
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL, -- 'alert', 'startup', 'shutdown', 'error', 'maintenance'
            severity TEXT DEFAULT 'info', -- 'info', 'warning', 'error', 'critical'
            panel_id TEXT,
            message TEXT NOT NULL,
            details_json TEXT,
            resolved BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMP,
            FOREIGN KEY (panel_id) REFERENCES panels (panel_id)
        )"""
        
        # Execute table creation
        cursor = self.connection.cursor()
        for sql in [panels_sql, readings_sql, aggregated_sql, system_aggregates_sql, events_sql]:
            cursor.execute(sql)
            
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_readings_panel_time ON panel_readings (panel_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON panel_readings (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_aggregates_panel_period ON panel_aggregates (panel_id, period_start, interval_type)",
            "CREATE INDEX IF NOT EXISTS idx_system_aggregates_period ON system_aggregates (period_start, interval_type)",
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_type ON system_events (event_type, severity)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
            
        self.connection.commit()
        self.logger.info("✅ Database tables created/verified")
        
    def add_panel(self, panel_id: str, location: str = None, sensor_address: str = None, 
                  notes: str = None) -> bool:
        """Add a new PS100 panel to the system"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO panels (panel_id, location, sensor_address, notes)
                VALUES (?, ?, ?, ?)
            """, (panel_id, location, sensor_address, notes))
            
            self.connection.commit()
            self.logger.info(f"✅ Added panel: {panel_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add panel {panel_id}: {e}")
            return False
            
    def log_reading(self, panel_id: str, voltage: float, current: float, power: float,
                   temperature: float = None, energy: float = None, 
                   alert_flags: dict = None, conditions: str = None) -> bool:
        """Log a real-time reading for a panel"""
        try:
            cursor = self.connection.cursor()
            
            alert_flags_json = json.dumps(alert_flags) if alert_flags else None
            
            cursor.execute("""
                INSERT INTO panel_readings 
                (panel_id, voltage, current, power, temperature, energy, alert_flags, conditions_estimate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (panel_id, voltage, current, power, temperature, energy, 
                  alert_flags_json, conditions))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to log reading for {panel_id}: {e}")
            return False
            
    def get_recent_readings(self, panel_id: str = None, hours: int = 24) -> List[Dict]:
        """Get recent readings for panel(s)"""
        try:
            cursor = self.connection.cursor()
            
            since = datetime.now() - timedelta(hours=hours)
            
            if panel_id:
                cursor.execute("""
                    SELECT * FROM panel_readings 
                    WHERE panel_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                """, (panel_id, since))
            else:
                cursor.execute("""
                    SELECT * FROM panel_readings 
                    WHERE timestamp > ?
                    ORDER BY panel_id, timestamp DESC
                """, (since,))
                
            if self.db_type == 'sqlite':
                return [dict(row) for row in cursor.fetchall()]
            else:
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"❌ Failed to get recent readings: {e}")
            return []
            
    def get_panel_summary(self, panel_id: str, days: int = 7) -> Dict:
        """Get summary statistics for a panel"""
        try:
            cursor = self.connection.cursor()
            
            since = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as reading_count,
                    MIN(voltage) as voltage_min,
                    MAX(voltage) as voltage_max,
                    AVG(voltage) as voltage_avg,
                    MIN(current) as current_min,
                    MAX(current) as current_max,
                    AVG(current) as current_avg,
                    MIN(power) as power_min,
                    MAX(power) as power_max,
                    AVG(power) as power_avg,
                    SUM(power) * 2.0 / 3600.0 as estimated_energy_kwh,
                    AVG(temperature) as temperature_avg,
                    MIN(timestamp) as first_reading,
                    MAX(timestamp) as last_reading
                FROM panel_readings
                WHERE panel_id = ? AND timestamp > ?
            """, (panel_id, since))
            
            row = cursor.fetchone()
            if self.db_type == 'sqlite':
                return dict(row) if row else {}
            else:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row)) if row else {}
                
        except Exception as e:
            self.logger.error(f"❌ Failed to get panel summary: {e}")
            return {}
            
    def log_event(self, event_type: str, message: str, panel_id: str = None, 
                  severity: str = 'info', details: dict = None) -> bool:
        """Log a system event"""
        try:
            cursor = self.connection.cursor()
            
            details_json = json.dumps(details) if details else None
            
            cursor.execute("""
                INSERT INTO system_events (event_type, severity, panel_id, message, details_json)
                VALUES (?, ?, ?, ?, ?)
            """, (event_type, severity, panel_id, message, details_json))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to log event: {e}")
            return False
            
    def cleanup_old_data(self, days_to_keep: int = 365) -> bool:
        """Clean up old raw readings (keep aggregates)"""
        try:
            cursor = self.connection.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            cursor.execute("""
                DELETE FROM panel_readings 
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            self.connection.commit()
            
            self.logger.info(f"✅ Cleaned up {deleted_count} old readings")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to cleanup old data: {e}")
            return False
            
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.logger.info("Database connection closed")

# Test the database setup
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🗄️  Testing PS100 Database Setup...")
    
    # Test SQLite database
    db = PS100Database()
    
    # Add a test panel
    db.add_panel("PS100_SOUTH_01", "South Roof", "0x40", "First PS100 panel")
    
    # Add some test readings
    import random
    for i in range(10):
        voltage = 20 + random.uniform(-2, 6)  # 18-26V range
        current = random.uniform(0.5, 4.0)     # 0.5-4A range
        power = voltage * current
        temperature = 25 + random.uniform(-5, 15)
        
        db.log_reading("PS100_SOUTH_01", voltage, current, power, temperature)
        
    # Test summary
    summary = db.get_panel_summary("PS100_SOUTH_01")
    print(f"📊 Panel Summary: {summary}")
    
    # Test event logging
    db.log_event("startup", "System started successfully", severity="info")
    
    db.close()
    print("✅ Database test complete!")
