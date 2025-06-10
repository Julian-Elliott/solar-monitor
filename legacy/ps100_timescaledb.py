#!/usr/bin/env python3
"""
PS100 TimescaleDB Integration
Optimized for Anker SOLIX PS100 solar panels with 1-second averaged permanent data storage

Features:
- TimescaleDB hypertables for time-series data
- 1-second averaged data with permanent retention
- Multiple PS100 panel support
- Continuous aggregation for analytics
- Data compression for storage efficiency
"""

import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import time
import asyncio
import numpy as np

# Load environment variables
load_dotenv()

class PS100TimescaleDB:
    """TimescaleDB manager for PS100 solar panel monitoring"""
    
    def __init__(self):
        """Initialize TimescaleDB connection for PS100 monitoring"""
        
        self.logger = logging.getLogger(__name__)
        
        # Connection parameters from environment
        self.db_config = {
            'host': os.getenv('TIMESCALE_HOST', 'localhost'),
            'port': int(os.getenv('TIMESCALE_PORT', 5432)),
            'user': os.getenv('TIMESCALE_USER'),
            'password': os.getenv('TIMESCALE_PASSWORD'),
            'database': os.getenv('TIMESCALE_DATABASE', 'solar_monitor')
        }
        
        self.connection = None
        self.cursor = None
        
        # Data aggregation buffer for 1-second averaging
        self.data_buffer = {}  # panel_id: list of readings within current second
        self.current_second = None
        
        self._connect()
        self._create_ps100_schema()
        
    def _connect(self):
        """Establish connection to TimescaleDB"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.connection.autocommit = True
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Test TimescaleDB extension
            self.cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';")
            result = self.cursor.fetchone()
            
            if result:
                self.logger.info(f"✅ Connected to TimescaleDB v{result['extversion']} at {self.db_config['host']}")
            else:
                raise Exception("TimescaleDB extension not found")
                
        except Exception as e:
            self.logger.error(f"❌ TimescaleDB connection failed: {e}")
            raise
            
    def _create_ps100_schema(self):
        """Create optimized schema for PS100 panel monitoring"""
        
        self.logger.info("🔧 Creating PS100 TimescaleDB schema...")
        
        # 1. Panel configuration table (regular PostgreSQL table)
        panels_sql = """
        CREATE TABLE IF NOT EXISTS ps100_panels (
            panel_id TEXT PRIMARY KEY,
            model TEXT DEFAULT 'Anker SOLIX PS100',
            location TEXT,
            sensor_address TEXT,
            installation_date TIMESTAMPTZ DEFAULT NOW(),
            rated_power REAL DEFAULT 100.0,
            rated_voltage REAL DEFAULT 26.5,
            rated_current REAL DEFAULT 3.77,
            max_current_fused REAL DEFAULT 10.0,
            active BOOLEAN DEFAULT TRUE,
            config JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        
        # 2. 1-second averaged readings (TimescaleDB hypertable)
        readings_sql = """
        CREATE TABLE IF NOT EXISTS ps100_readings_1s (
            time TIMESTAMPTZ NOT NULL,
            panel_id TEXT NOT NULL,
            
            -- Electrical measurements (1-second averages)
            voltage_avg REAL NOT NULL,
            voltage_min REAL NOT NULL,
            voltage_max REAL NOT NULL,
            voltage_stddev REAL,
            
            current_avg REAL NOT NULL,
            current_min REAL NOT NULL,
            current_max REAL NOT NULL,
            current_stddev REAL,
            
            power_avg REAL NOT NULL,
            power_min REAL NOT NULL,
            power_max REAL NOT NULL,
            power_peak REAL NOT NULL,
            
            -- Energy calculation (Wh for this second)
            energy_wh REAL NOT NULL,
            
            -- Environmental
            temperature_avg REAL,
            temperature_min REAL,
            temperature_max REAL,
            
            -- Data quality metrics
            sample_count INTEGER NOT NULL,
            alert_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            conditions_estimate TEXT,
            
            -- Performance metrics
            efficiency_percent REAL,
            power_factor REAL DEFAULT 1.0,
            
            -- Metadata
            alerts JSONB,
            quality_flags JSONB,
            
            FOREIGN KEY (panel_id) REFERENCES ps100_panels(panel_id),
            UNIQUE (time, panel_id)
        );
        """
        
        # 3. System-wide aggregates (1-second resolution)
        system_sql = """
        CREATE TABLE IF NOT EXISTS ps100_system_1s (
            time TIMESTAMPTZ NOT NULL,
            
            -- System totals
            total_power_avg REAL NOT NULL,
            total_power_peak REAL NOT NULL,
            total_current_avg REAL NOT NULL,
            total_energy_wh REAL NOT NULL,
            
            -- System metrics
            active_panels INTEGER NOT NULL,
            total_panels INTEGER NOT NULL,
            system_efficiency_percent REAL,
            system_voltage_avg REAL,
            
            -- Performance
            best_panel_id TEXT,
            worst_panel_id TEXT,
            best_panel_power REAL,
            worst_panel_power REAL,
            
            -- Quality metrics
            total_alerts INTEGER DEFAULT 0,
            total_errors INTEGER DEFAULT 0,
            data_quality_percent REAL DEFAULT 100.0,
            
            PRIMARY KEY (time)
        );
        """
        
        # 4. Events and alerts table
        events_sql = """
        CREATE TABLE IF NOT EXISTS ps100_events (
            id SERIAL PRIMARY KEY,
            time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            panel_id TEXT,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            message TEXT NOT NULL,
            details JSONB,
            resolved BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMPTZ,
            
            FOREIGN KEY (panel_id) REFERENCES ps100_panels(panel_id)
        );
        """
        
        # Execute table creation
        for sql in [panels_sql, readings_sql, system_sql, events_sql]:
            self.cursor.execute(sql)
            
        # Convert readings table to hypertable (if not already)
        try:
            self.cursor.execute("""
                SELECT create_hypertable('ps100_readings_1s', 'time', 
                                       chunk_time_interval => INTERVAL '1 day',
                                       if_not_exists => TRUE);
            """)
            self.logger.info("✅ Created hypertable: ps100_readings_1s")
        except Exception as e:
            self.logger.warning(f"Hypertable creation skipped: {e}")
            
        # Convert system table to hypertable
        try:
            self.cursor.execute("""
                SELECT create_hypertable('ps100_system_1s', 'time',
                                       chunk_time_interval => INTERVAL '1 day',
                                       if_not_exists => TRUE);
            """)
            self.logger.info("✅ Created hypertable: ps100_system_1s")
        except Exception as e:
            self.logger.warning(f"System hypertable creation skipped: {e}")
            
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ps100_readings_panel_time ON ps100_readings_1s (panel_id, time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_ps100_readings_time ON ps100_readings_1s (time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_ps100_system_time ON ps100_system_1s (time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_ps100_events_time ON ps100_events (time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_ps100_events_panel ON ps100_events (panel_id, time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_ps100_events_type ON ps100_events (event_type, severity);"
        ]
        
        for index_sql in indexes:
            try:
                self.cursor.execute(index_sql)
            except Exception as e:
                self.logger.warning(f"Index creation warning: {e}")
                
        # Setup continuous aggregates for longer time periods
        self._create_continuous_aggregates()
        
        # Setup data retention and compression policies
        self._setup_retention_policies()
        
        self.logger.info("✅ PS100 TimescaleDB schema created successfully")
        
    def _create_continuous_aggregates(self):
        """Create continuous aggregates for different time periods"""
        
        # 5-minute aggregates
        cagg_5min_sql = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS ps100_readings_5min
        WITH (timescaledb.continuous) AS
        SELECT 
            time_bucket('5 minutes', time) AS time,
            panel_id,
            AVG(voltage_avg) AS voltage_avg,
            MIN(voltage_min) AS voltage_min,
            MAX(voltage_max) AS voltage_max,
            AVG(current_avg) AS current_avg,
            MIN(current_min) AS current_min,
            MAX(current_max) AS current_max,
            AVG(power_avg) AS power_avg,
            MIN(power_min) AS power_min,
            MAX(power_max) AS power_max,
            MAX(power_peak) AS power_peak,
            SUM(energy_wh) AS energy_wh,
            AVG(temperature_avg) AS temperature_avg,
            SUM(sample_count) AS sample_count,
            SUM(alert_count) AS alert_count,
            AVG(efficiency_percent) AS efficiency_percent
        FROM ps100_readings_1s
        GROUP BY time_bucket('5 minutes', time), panel_id;
        """
        
        # 1-hour aggregates
        cagg_1hour_sql = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS ps100_readings_1hour
        WITH (timescaledb.continuous) AS
        SELECT 
            time_bucket('1 hour', time) AS time,
            panel_id,
            AVG(voltage_avg) AS voltage_avg,
            MIN(voltage_min) AS voltage_min,
            MAX(voltage_max) AS voltage_max,
            AVG(current_avg) AS current_avg,
            MIN(current_min) AS current_min,
            MAX(current_max) AS current_max,
            AVG(power_avg) AS power_avg,
            MIN(power_min) AS power_min,
            MAX(power_max) AS power_max,
            MAX(power_peak) AS power_peak,
            SUM(energy_wh) AS energy_wh,
            AVG(temperature_avg) AS temperature_avg,
            SUM(sample_count) AS sample_count,
            SUM(alert_count) AS alert_count,
            AVG(efficiency_percent) AS efficiency_percent
        FROM ps100_readings_1s
        GROUP BY time_bucket('1 hour', time), panel_id;
        """
        
        # Daily aggregates
        cagg_daily_sql = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS ps100_readings_daily
        WITH (timescaledb.continuous) AS
        SELECT 
            time_bucket('1 day', time) AS time,
            panel_id,
            AVG(voltage_avg) AS voltage_avg,
            MIN(voltage_min) AS voltage_min,
            MAX(voltage_max) AS voltage_max,
            AVG(current_avg) AS current_avg,
            MIN(current_min) AS current_min,
            MAX(current_max) AS current_max,
            AVG(power_avg) AS power_avg,
            MIN(power_min) AS power_min,
            MAX(power_max) AS power_max,
            MAX(power_peak) AS power_peak,
            SUM(energy_wh) / 1000.0 AS energy_kwh,  -- Convert to kWh
            AVG(temperature_avg) AS temperature_avg,
            SUM(sample_count) AS sample_count,
            SUM(alert_count) AS alert_count,
            AVG(efficiency_percent) AS efficiency_percent
        FROM ps100_readings_1s
        GROUP BY time_bucket('1 day', time), panel_id;
        """
        
        # Create continuous aggregates
        for cagg_sql in [cagg_5min_sql, cagg_1hour_sql, cagg_daily_sql]:
            try:
                self.cursor.execute(cagg_sql)
            except Exception as e:
                self.logger.warning(f"Continuous aggregate creation warning: {e}")
                
        self.logger.info("✅ Continuous aggregates created")
        
    def _setup_retention_policies(self):
        """Setup data retention and compression policies"""
        
        try:
            # Compress data older than 7 days
            self.cursor.execute("""
                SELECT add_compression_policy('ps100_readings_1s', INTERVAL '7 days');
            """)
            self.logger.info("✅ Compression policy added (7 days)")
        except Exception as e:
            self.logger.warning(f"Compression policy warning: {e}")
            
        # Note: No retention policy - data is permanent as requested
        self.logger.info("📊 Data retention: PERMANENT (no deletion policy)")
        
    def add_panel(self, panel_id: str, location: str = None, sensor_address: str = None,
                  notes: str = None) -> bool:
        """Add a new PS100 panel to the system"""
        try:
            config = {
                'model': 'Anker SOLIX PS100',
                'notes': notes,
                'added_by': 'ps100_monitor'
            }
            
            self.cursor.execute("""
                INSERT INTO ps100_panels (panel_id, location, sensor_address, config)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (panel_id) DO UPDATE SET
                    location = EXCLUDED.location,
                    sensor_address = EXCLUDED.sensor_address,
                    config = EXCLUDED.config,
                    updated_at = NOW()
            """, (panel_id, location, sensor_address, json.dumps(config)))
            
            self.logger.info(f"✅ Added/updated panel: {panel_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add panel {panel_id}: {e}")
            return False
            
    def buffer_reading(self, panel_id: str, voltage: float, current: float, power: float,
                      temperature: float = None, energy: float = None, 
                      alert_flags: dict = None, conditions: str = None) -> bool:
        """Buffer a reading for 1-second aggregation"""
        
        try:
            current_time = datetime.now()
            current_second = current_time.replace(microsecond=0)
            
            # Initialize buffer for new second
            if self.current_second != current_second:
                if self.current_second is not None:
                    # Process previous second's data
                    self._flush_buffer()
                    
                self.current_second = current_second
                self.data_buffer = {}
                
            # Add reading to buffer
            if panel_id not in self.data_buffer:
                self.data_buffer[panel_id] = []
                
            reading = {
                'timestamp': current_time,
                'voltage': voltage,
                'current': current,
                'power': power,
                'temperature': temperature,
                'energy': energy or 0,
                'alerts': alert_flags or {},
                'conditions': conditions,
                'has_alerts': bool(alert_flags and any(alert_flags.values()))
            }
            
            self.data_buffer[panel_id].append(reading)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to buffer reading for {panel_id}: {e}")
            return False
            
    def _flush_buffer(self):
        """Process buffered readings and insert 1-second averages"""
        
        if not self.data_buffer or not self.current_second:
            return
            
        try:
            # Process each panel's data for this second
            panel_aggregates = []
            system_totals = {
                'total_power': 0,
                'total_current': 0,
                'total_energy': 0,
                'active_panels': 0,
                'total_alerts': 0,
                'voltages': [],
                'powers': [],
                'panel_powers': {}
            }
            
            for panel_id, readings in self.data_buffer.items():
                if not readings:
                    continue
                    
                # Calculate statistics for this panel over the second
                voltages = [r['voltage'] for r in readings]
                currents = [r['current'] for r in readings]
                powers = [r['power'] for r in readings]
                temperatures = [r['temperature'] for r in readings if r['temperature'] is not None]
                energies = [r['energy'] for r in readings]
                
                alert_count = sum(1 for r in readings if r['has_alerts'])
                
                # Calculate aggregates
                voltage_avg = np.mean(voltages)
                voltage_min = np.min(voltages)
                voltage_max = np.max(voltages)
                voltage_std = np.std(voltages) if len(voltages) > 1 else 0
                
                current_avg = np.mean(currents)
                current_min = np.min(currents)
                current_max = np.max(currents)
                current_std = np.std(currents) if len(currents) > 1 else 0
                
                power_avg = np.mean(powers)
                power_min = np.min(powers)
                power_max = np.max(powers)
                power_peak = np.max(powers)
                
                # Energy in Wh for this second (power * time / 3600)
                energy_wh = power_avg / 3600.0
                
                temp_avg = np.mean(temperatures) if temperatures else None
                temp_min = np.min(temperatures) if temperatures else None
                temp_max = np.max(temperatures) if temperatures else None
                
                # Calculate efficiency (compared to PS100 rated 100W)
                efficiency = (power_avg / 100.0) * 100 if power_avg > 0 else 0
                
                # Get latest conditions estimate
                latest_conditions = readings[-1]['conditions'] or 'Unknown'
                
                # Store aggregate (convert numpy types to Python types)
                panel_aggregate = {
                    'time': self.current_second,
                    'panel_id': panel_id,
                    'voltage_avg': float(voltage_avg),
                    'voltage_min': float(voltage_min),
                    'voltage_max': float(voltage_max),
                    'voltage_stddev': float(voltage_std),
                    'current_avg': float(current_avg),
                    'current_min': float(current_min),
                    'current_max': float(current_max),
                    'current_stddev': float(current_std),
                    'power_avg': float(power_avg),
                    'power_min': float(power_min),
                    'power_max': float(power_max),
                    'power_peak': float(power_peak),
                    'energy_wh': float(energy_wh),
                    'temperature_avg': float(temp_avg) if temp_avg is not None else None,
                    'temperature_min': float(temp_min) if temp_min is not None else None,
                    'temperature_max': float(temp_max) if temp_max is not None else None,
                    'sample_count': len(readings),
                    'alert_count': alert_count,
                    'error_count': 0,  # TODO: track errors
                    'conditions_estimate': latest_conditions,
                    'efficiency_percent': float(efficiency),
                    'power_factor': 1.0,  # PS100 is DC, so PF = 1
                    'alerts': json.dumps(readings[-1]['alerts']),
                    'quality_flags': json.dumps({'std_voltage': float(voltage_std), 'std_current': float(current_std)})
                }
                
                panel_aggregates.append(panel_aggregate)
                
                # Update system totals (convert numpy types to Python types)
                system_totals['total_power'] += float(power_avg)
                system_totals['total_current'] += float(current_avg)
                system_totals['total_energy'] += float(energy_wh)
                system_totals['active_panels'] += 1
                system_totals['total_alerts'] += alert_count
                system_totals['voltages'].append(float(voltage_avg))
                system_totals['powers'].append(float(power_avg))
                system_totals['panel_powers'][panel_id] = float(power_avg)
                
            # Insert panel aggregates
            if panel_aggregates:
                self._insert_panel_aggregates(panel_aggregates)
                
            # Insert system aggregate
            if system_totals['active_panels'] > 0:
                self._insert_system_aggregate(system_totals)
                
        except Exception as e:
            self.logger.error(f"❌ Failed to flush buffer: {e}")
            
    def _insert_panel_aggregates(self, aggregates: List[Dict]):
        """Insert panel aggregates to TimescaleDB"""
        
        insert_sql = """
        INSERT INTO ps100_readings_1s (
            time, panel_id, voltage_avg, voltage_min, voltage_max, voltage_stddev,
            current_avg, current_min, current_max, current_stddev,
            power_avg, power_min, power_max, power_peak, energy_wh,
            temperature_avg, temperature_min, temperature_max,
            sample_count, alert_count, error_count, conditions_estimate,
            efficiency_percent, power_factor, alerts, quality_flags
        ) VALUES (
            %(time)s, %(panel_id)s, %(voltage_avg)s, %(voltage_min)s, %(voltage_max)s, %(voltage_stddev)s,
            %(current_avg)s, %(current_min)s, %(current_max)s, %(current_stddev)s,
            %(power_avg)s, %(power_min)s, %(power_max)s, %(power_peak)s, %(energy_wh)s,
            %(temperature_avg)s, %(temperature_min)s, %(temperature_max)s,
            %(sample_count)s, %(alert_count)s, %(error_count)s, %(conditions_estimate)s,
            %(efficiency_percent)s, %(power_factor)s, %(alerts)s, %(quality_flags)s
        )
        ON CONFLICT (time, panel_id) DO UPDATE SET
            voltage_avg = EXCLUDED.voltage_avg,
            current_avg = EXCLUDED.current_avg,
            power_avg = EXCLUDED.power_avg,
            energy_wh = EXCLUDED.energy_wh,
            sample_count = EXCLUDED.sample_count
        """
        
        psycopg2.extras.execute_batch(self.cursor, insert_sql, aggregates)
        
    def _insert_system_aggregate(self, totals: Dict):
        """Insert system-wide aggregate"""
        
        # Find best and worst performing panels
        panel_powers = totals['panel_powers']
        best_panel_id = max(panel_powers, key=panel_powers.get) if panel_powers else None
        worst_panel_id = min(panel_powers, key=panel_powers.get) if panel_powers else None
        
        system_agg = {
            'time': self.current_second,
            'total_power_avg': totals['total_power'],
            'total_power_peak': max(totals['powers']) if totals['powers'] else 0,
            'total_current_avg': totals['total_current'],
            'total_energy_wh': totals['total_energy'],
            'active_panels': totals['active_panels'],
            'total_panels': len(self.data_buffer),
            'system_efficiency_percent': (totals['total_power'] / (totals['active_panels'] * 100)) * 100 if totals['active_panels'] > 0 else 0,
            'system_voltage_avg': float(np.mean(totals['voltages'])) if totals['voltages'] else 0,
            'best_panel_id': best_panel_id,
            'worst_panel_id': worst_panel_id,
            'best_panel_power': panel_powers.get(best_panel_id, 0) if best_panel_id else 0,
            'worst_panel_power': panel_powers.get(worst_panel_id, 0) if worst_panel_id else 0,
            'total_alerts': totals['total_alerts'],
            'total_errors': 0,
            'data_quality_percent': 100.0
        }
        
        insert_sql = """
        INSERT INTO ps100_system_1s (
            time, total_power_avg, total_power_peak, total_current_avg, total_energy_wh,
            active_panels, total_panels, system_efficiency_percent, system_voltage_avg,
            best_panel_id, worst_panel_id, best_panel_power, worst_panel_power,
            total_alerts, total_errors, data_quality_percent
        ) VALUES (
            %(time)s, %(total_power_avg)s, %(total_power_peak)s, %(total_current_avg)s, %(total_energy_wh)s,
            %(active_panels)s, %(total_panels)s, %(system_efficiency_percent)s, %(system_voltage_avg)s,
            %(best_panel_id)s, %(worst_panel_id)s, %(best_panel_power)s, %(worst_panel_power)s,
            %(total_alerts)s, %(total_errors)s, %(data_quality_percent)s
        )
        ON CONFLICT (time) DO UPDATE SET
            total_power_avg = EXCLUDED.total_power_avg,
            total_current_avg = EXCLUDED.total_current_avg,
            active_panels = EXCLUDED.active_panels
        """
        
        self.cursor.execute(insert_sql, system_agg)
        
    def force_flush(self):
        """Force flush current buffer (call before shutdown)"""
        if self.data_buffer:
            self._flush_buffer()
            self.data_buffer = {}
            
    def log_event(self, event_type: str, message: str, panel_id: str = None,
                  severity: str = 'info', details: dict = None) -> bool:
        """Log a system event"""
        try:
            self.cursor.execute("""
                INSERT INTO ps100_events (panel_id, event_type, severity, message, details)
                VALUES (%s, %s, %s, %s, %s)
            """, (panel_id, event_type, severity, message, json.dumps(details) if details else None))
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to log event: {e}")
            return False
            
    def get_recent_data(self, panel_id: str = None, hours: int = 24) -> List[Dict]:
        """Get recent 1-second data"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            if panel_id:
                self.cursor.execute("""
                    SELECT * FROM ps100_readings_1s
                    WHERE panel_id = %s AND time > %s
                    ORDER BY time DESC
                    LIMIT 1000
                """, (panel_id, since))
            else:
                self.cursor.execute("""
                    SELECT * FROM ps100_readings_1s
                    WHERE time > %s
                    ORDER BY time DESC, panel_id
                    LIMIT 1000
                """, (since,))
                
            return [dict(row) for row in self.cursor.fetchall()]
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get recent data: {e}")
            return []
            
    def get_daily_summary(self, panel_id: str = None, days: int = 7) -> List[Dict]:
        """Get daily summaries using continuous aggregates"""
        try:
            since = datetime.now() - timedelta(days=days)
            
            if panel_id:
                self.cursor.execute("""
                    SELECT * FROM ps100_readings_daily
                    WHERE panel_id = %s AND time > %s
                    ORDER BY time DESC
                """, (panel_id, since))
            else:
                self.cursor.execute("""
                    SELECT 
                        time,
                        COUNT(*) as panel_count,
                        AVG(voltage_avg) as system_voltage_avg,
                        SUM(energy_kwh) as total_energy_kwh,
                        AVG(power_avg) as avg_power,
                        MAX(power_peak) as peak_power,
                        AVG(efficiency_percent) as avg_efficiency
                    FROM ps100_readings_daily
                    WHERE time > %s
                    GROUP BY time
                    ORDER BY time DESC
                """, (since,))
                
            return [dict(row) for row in self.cursor.fetchall()]
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get daily summary: {e}")
            return []
            
    def close(self):
        """Close database connection"""
        self.force_flush()  # Flush any remaining data
        
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.logger.info("TimescaleDB connection closed")

# Test the TimescaleDB setup
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🗄️  Testing PS100 TimescaleDB Setup...")
    
    try:
        # Test database connection and schema
        db = PS100TimescaleDB()
        
        # Add a test panel
        db.add_panel("PS100_TEST_01", "Test Location", "0x40", "Test PS100 panel")
        
        # Add some test readings with averaging
        import random
        print("📊 Adding test readings...")
        
        for second in range(5):
            # Simulate multiple readings per second
            for reading in range(10):  # 10 readings per second
                voltage = 25.0 + random.uniform(-1, 2)
                current = 3.0 + random.uniform(-0.5, 1.0)
                power = voltage * current
                temperature = 30 + random.uniform(-5, 10)
                
                db.buffer_reading("PS100_TEST_01", voltage, current, power, temperature)
                
            time.sleep(1)  # Wait for next second
            
        # Force flush final data
        db.force_flush()
        
        # Test data retrieval
        recent_data = db.get_recent_data("PS100_TEST_01", hours=1)
        print(f"📈 Retrieved {len(recent_data)} 1-second aggregates")
        
        if recent_data:
            latest = recent_data[0]
            print(f"   Latest: {latest['power_avg']:.1f}W avg, {latest['sample_count']} samples")
            
        # Test system summary
        daily_summary = db.get_daily_summary(days=1)
        print(f"📅 Daily summary entries: {len(daily_summary)}")
        
        db.close()
        print("✅ TimescaleDB test complete!")
        
    except Exception as e:
        print(f"❌ TimescaleDB test failed: {e}")
        import traceback
        traceback.print_exc()
