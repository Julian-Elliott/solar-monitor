"""
TimescaleDB Database Interface
Handles all database operations for PS100 readings
"""

import os
import json
import logging
from typing import Dict, Any, List

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


class PS100Database:
    """TimescaleDB interface for PS100 readings"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_timescale()
    
    def _setup_timescale(self):
        """Setup TimescaleDB connection"""
        load_dotenv('config/.env')
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('TIMESCALE_HOST'),
                port=os.getenv('TIMESCALE_PORT'),
                user=os.getenv('TIMESCALE_USER'),
                password=os.getenv('TIMESCALE_PASSWORD'),
                database=os.getenv('TIMESCALE_DATABASE')
            )
            self.cursor = self.conn.cursor()
            
            # Create hypertable
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS ps100_readings (
                    time TIMESTAMPTZ NOT NULL,
                    panel_id TEXT NOT NULL,
                    voltage REAL NOT NULL,
                    current REAL NOT NULL,
                    power REAL NOT NULL,
                    energy_wh REAL,
                    temperature REAL,
                    efficiency_percent REAL,
                    conditions TEXT,
                    alerts JSONB,
                    PRIMARY KEY (time, panel_id)
                )
            """)
            
            # Create hypertable if not exists
            try:
                self.cursor.execute("SELECT create_hypertable('ps100_readings', 'time', if_not_exists => TRUE)")
            except:
                pass  # Already exists
                
            self.conn.commit()
            self.logger.info("✅ TimescaleDB initialized")
        except Exception as e:
            self.logger.error(f"❌ TimescaleDB connection failed: {e}")
            raise
    
    def store_reading(self, reading: Dict[str, Any]):
        """Store a reading in TimescaleDB"""
        if not reading:
            return
            
        try:
            self.cursor.execute("""
                INSERT INTO ps100_readings 
                (time, panel_id, voltage, current, power, energy_wh, temperature, 
                 efficiency_percent, conditions, alerts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, panel_id) DO UPDATE SET
                    voltage = EXCLUDED.voltage,
                    power = EXCLUDED.power
            """, (
                reading['timestamp'], reading['panel_id'],
                reading['voltage'], reading['current'], reading['power'],
                reading['energy_wh'], reading['temperature'],
                reading['efficiency_percent'], reading['conditions'],
                json.dumps(reading['alerts'])
            ))
            self.conn.commit()
            self.logger.debug(f"📊 Stored: {reading['power']:.1f}W")
        except Exception as e:
            self.logger.error(f"❌ Database store failed: {e}")
    
    def get_recent_readings(self, limit: int = 10) -> List[Dict]:
        """Get recent readings from TimescaleDB"""
        try:
            self.cursor.execute("""
                SELECT time, panel_id, voltage, current, power, conditions
                FROM ps100_readings 
                ORDER BY time DESC LIMIT %s
            """, (limit,))
            rows = self.cursor.fetchall()
            return [{'time': r[0], 'panel_id': r[1], 'voltage': r[2], 
                    'current': r[3], 'power': r[4], 'conditions': r[5]} for r in rows]
        except Exception as e:
            self.logger.error(f"❌ Database query failed: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
