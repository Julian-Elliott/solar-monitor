#!/usr/bin/env python3
"""
PS100 Solar Monitor - TimescaleDB Implementation
Monitoring system for Anker SOLIX PS100 panels with TimescaleDB storage
"""

import os
import sys
import time
import json
import asyncio
import logging
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import board
import adafruit_ina228
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

@dataclass
class PS100Config:
    """PS100 panel configuration"""
    RATED_VOLTAGE = 26.5    # Vmp - Maximum Power Voltage
    RATED_CURRENT = 3.77    # Imp - Maximum Power Current  
    RATED_POWER = 100       # Watts
    SHUNT_RESISTANCE = 0.015  # 15mΩ integrated shunt
    MAX_CURRENT = 10.0      # 10A fuse rating
    MAX_VOLTAGE = 30.0      # Safety margin

class PS100Sensor:
    """Simplified INA228 sensor interface for PS100"""
    
    def __init__(self, address: int = 0x40):
        self.address = address
        self.config = PS100Config()
        self._setup_sensor()
    
    def _setup_sensor(self):
        """Initialize INA228 with PS100 settings"""
        try:
            i2c = board.I2C()
            self.ina228 = adafruit_ina228.INA228(i2c, self.address, self.config.SHUNT_RESISTANCE)
            
            # Configure averaging and conversion times
            self.ina228.averaging_count = adafruit_ina228.AveragingCount.COUNT_64
            self.ina228.conversion_time_bus = adafruit_ina228.ConversionTime.TIME_1052_US
            self.ina228.conversion_time_shunt = adafruit_ina228.ConversionTime.TIME_1052_US
            
            # Set safety limits
            self.ina228.current_limit = 9.5  # Below 10A fuse
            self.ina228.voltage_limit = 28.0  # Above normal operation
            
            logging.info(f"✅ PS100 sensor initialized at 0x{self.address:02X}")
        except Exception as e:
            logging.error(f"❌ Sensor initialization failed: {e}")
            raise
    
    def read(self) -> Dict[str, Any]:
        """Read sensor data and return structured reading"""
        try:
            # Raw readings
            voltage = float(self.ina228.bus_voltage)
            current = float(self.ina228.current)
            power = float(self.ina228.power)
            temp = float(self.ina228.die_temperature)
            
            # Calculate derived values
            energy_wh = power / 3600.0  # Wh for this second
            efficiency = (power / self.config.RATED_POWER) * 100 if power > 0 else 0
            
            # Determine conditions
            conditions = self._assess_conditions(voltage, current, power)
            
            # Check alerts
            alerts = self.ina228.alert_flags
            has_alerts = any(alerts.values())
            
            return {
                'timestamp': datetime.now(timezone.utc),
                'voltage': voltage,
                'current': current, 
                'power': power,
                'energy_wh': energy_wh,
                'temperature': temp,
                'efficiency_percent': efficiency,
                'conditions': conditions,
                'alerts': alerts,
                'has_alerts': has_alerts,
                'panel_id': f'PS100_0X{self.address:02X}'
            }
        except Exception as e:
            logging.error(f"❌ Sensor read failed: {e}")
            return None
    
    def _assess_conditions(self, voltage: float, current: float, power: float) -> str:
        """Assess solar conditions based on readings"""
        if power > 90:
            return "Excellent - Full sun"
        elif power > 50:
            return "Good - Partial sun" 
        elif power > 10:
            return "Poor - Heavy clouds/shade"
        elif voltage < 18:
            return "No generation"
        else:
            return "Poor - Heavy clouds/shade"

class PS100Database:
    """TimescaleDB interface for PS100 readings"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_timescale()
    
    def _setup_timescale(self):
        """Setup TimescaleDB connection"""
        load_dotenv()
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

class PS100Monitor:
    """PS100 monitoring system with TimescaleDB"""
    
    def __init__(self, addresses: List[int] = None):
        self.addresses = addresses or [0x40]
        self.sensors = {}
        self.database = None
        self.running = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self._setup_components()
    
    def _setup_components(self):
        """Initialize sensors and database"""
        # Initialize sensors
        for addr in self.addresses:
            try:
                sensor = PS100Sensor(addr)
                panel_id = f'PS100_0X{addr:02X}'
                self.sensors[panel_id] = sensor
                self.logger.info(f"✅ Sensor {panel_id} ready")
            except Exception as e:
                self.logger.error(f"❌ Failed to init sensor at 0x{addr:02X}: {e}")
        
        if not self.sensors:
            raise RuntimeError("No sensors initialized successfully")
        
        # Initialize TimescaleDB
        self.database = PS100Database()
        self.logger.info("✅ Database (TimescaleDB) ready")
    
    async def run_monitor(self, read_interval: float = 1.0):
        """Main monitoring loop"""
        self.running = True
        self.logger.info(f"🚀 PS100 Monitor started - {len(self.sensors)} panels")
        
        try:
            while self.running:
                start_time = time.time()
                
                # Read all sensors
                for panel_id, sensor in self.sensors.items():
                    reading = sensor.read()
                    if reading:
                        self.database.store_reading(reading)
                        
                        # Log significant changes
                        if reading['power'] > 5 or reading['has_alerts']:
                            self.logger.info(
                                f"📊 {panel_id}: {reading['power']:.1f}W "
                                f"({reading['voltage']:.1f}V × {reading['current']:.2f}A) "
                                f"- {reading['conditions']}"
                            )
                
                # Sleep for remaining interval
                elapsed = time.time() - start_time
                sleep_time = max(0, read_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Monitor stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Monitor error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop monitoring and cleanup"""
        self.running = False
        if self.database:
            self.database.close()
        self.logger.info("✅ PS100 Monitor stopped")
    
    def status(self) -> Dict[str, Any]:
        """Get current system status"""
        recent = self.database.get_recent_readings(1)
        latest = recent[0] if recent else None
        
        return {
            'sensors': len(self.sensors),
            'database': "TimescaleDB",
            'latest_reading': latest,
            'running': self.running
        }

def main():
    """Main entry point with command line interface"""
    parser = argparse.ArgumentParser(description='PS100 Solar Monitor - TimescaleDB')
    parser.add_argument('--addresses', nargs='+', type=lambda x: int(x, 0), 
                       default=[0x40], help='I2C addresses (e.g., 0x40 0x41)')
    parser.add_argument('--interval', type=float, default=1.0, help='Read interval in seconds')
    parser.add_argument('--test', action='store_true', help='Run test mode (single reading)')
    parser.add_argument('--status', action='store_true', help='Show current status')
    
    args = parser.parse_args()
    
    try:
        monitor = PS100Monitor(addresses=args.addresses)
        
        if args.test:
            # Test mode - single reading
            print("🧪 PS100 Test Mode")
            for panel_id, sensor in monitor.sensors.items():
                reading = sensor.read()
                if reading:
                    print(f"📊 {panel_id}:")
                    print(f"   Voltage: {reading['voltage']:.2f}V")
                    print(f"   Current: {reading['current']:.2f}A") 
                    print(f"   Power: {reading['power']:.1f}W")
                    print(f"   Efficiency: {reading['efficiency_percent']:.1f}%")
                    print(f"   Conditions: {reading['conditions']}")
                    
        elif args.status:
            # Status mode
            status = monitor.status()
            print(f"📊 PS100 Status:")
            print(f"   Sensors: {status['sensors']}")
            print(f"   Database: {status['database']}")
            if status['latest_reading']:
                latest = status['latest_reading']
                print(f"   Latest: {latest['power']:.1f}W - {latest['conditions']}")
                
        else:
            # Monitor mode
            asyncio.run(monitor.run_monitor(args.interval))
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
