#!/usr/bin/env python3
"""
Solar Monitor Data Logger
Continuously reads INA228 sensor data and stores it in TimescaleDB
Optimized for high-frequency data collection with calibration fix
"""

import os
import time
import logging
import signal
import sys
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass
import board
import adafruit_ina228
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
from sensor_calibration_patch import apply_solar_calibration

# Load environment variables
load_dotenv()


@dataclass
class SensorReading:
    """Data class for sensor readings"""
    timestamp: datetime
    voltage: float
    current: float
    power: float
    shunt_voltage: float
    temperature: float
    energy: float
    charge: float


class SolarDataLogger:
    """High-performance solar data logger for TimescaleDB"""
    
    def __init__(self):
        self.setup_logging()
        self.sensor = None
        self.db_connection = None
        self.running = False
        self.readings_buffer = []
        
        # Configuration from environment
        self.read_interval = float(os.getenv('SENSOR_READ_INTERVAL', 0.1))
        self.batch_size = int(os.getenv('BATCH_SIZE', 100))
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('TIMESCALE_HOST'),
            'port': os.getenv('TIMESCALE_PORT'),
            'user': os.getenv('TIMESCALE_USER'),
            'password': os.getenv('TIMESCALE_PASSWORD'),
            'database': os.getenv('TIMESCALE_DATABASE')
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Configure logging"""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('solar_monitor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def init_sensor(self):
        """Initialize the INA228 sensor"""
        try:
            self.logger.info("Initializing INA228 sensor...")
            i2c = board.I2C()
            self.sensor = adafruit_ina228.INA228(i2c)
            
            # Apply solar monitoring calibration fix
            apply_solar_calibration(self.sensor)
            self.logger.info("🔧 Applied solar calibration (0.1Ω, 1A)")
            
            # Log sensor information
            self.logger.info("✅ INA228 connected successfully!")
            avg_count = self.sensor.averaging_count
            self.logger.info(f"📋 Averaging: {avg_count} samples")
            voltage = self.sensor.bus_voltage
            self.logger.info(f"📋 Voltage: {voltage:.3f}V")
            current_ma = self.sensor.current * 1000
            self.logger.info(f"📋 Current: {current_ma:.1f}mA")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize sensor: {e}")
            return False
    
    def init_database(self):
        """Initialize database connection and create tables"""
        try:
            self.logger.info("Connecting to TimescaleDB...")
            self.db_connection = psycopg2.connect(**self.db_config)
            self.db_connection.autocommit = True
            
            # Create the table if it doesn't exist
            self.create_tables()
            self.logger.info("✅ Database connected successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    def create_tables(self):
        """Create the solar data table and hypertable"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS solar_readings (
            timestamp TIMESTAMPTZ NOT NULL,
            voltage DOUBLE PRECISION NOT NULL,
            current DOUBLE PRECISION NOT NULL,
            power DOUBLE PRECISION NOT NULL,
            shunt_voltage DOUBLE PRECISION NOT NULL,
            temperature DOUBLE PRECISION NOT NULL,
            energy DOUBLE PRECISION NOT NULL,
            charge DOUBLE PRECISION NOT NULL
        );
        """
        
        # Create hypertable for time-series optimization
        hypertable_sql = """
        SELECT create_hypertable('solar_readings', 'timestamp', 
                                if_not_exists => TRUE);
        """
        
        with self.db_connection.cursor() as cursor:
            cursor.execute(create_table_sql)
            try:
                cursor.execute(hypertable_sql)
                self.logger.info("📊 Hypertable created/verified")
            except Exception as e:
                # Hypertable might already exist
                self.logger.info(f"Hypertable note: {e}")
    
    def read_sensor(self) -> SensorReading:
        """Read data from the INA228 sensor"""
        try:
            timestamp = datetime.utcnow()
            
            # Read all sensor values
            reading = SensorReading(
                timestamp=timestamp,
                voltage=self.sensor.bus_voltage,
                current=self.sensor.current,
                power=self.sensor.power,
                shunt_voltage=self.sensor.shunt_voltage,
                temperature=self.sensor.die_temperature,
                energy=self.sensor.energy,
                charge=self.sensor.charge
            )
            
            return reading
            
        except Exception as e:
            self.logger.error(f"Error reading sensor: {e}")
            return
    
    def insert_readings_batch(self, readings: List[SensorReading]):
        """Insert a batch of readings into the database"""
        insert_sql = """
        INSERT INTO solar_readings 
        (timestamp, voltage, current, power, shunt_voltage, temperature, 
         energy, charge)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Convert readings to tuples for batch insert
        data = [
            (
                r.timestamp, r.voltage, r.current, r.power,
                r.shunt_voltage, r.temperature, r.energy, r.charge
            )
            for r in readings
        ]
        
        try:
            with self.db_connection.cursor() as cursor:
                execute_batch(cursor, insert_sql, data, page_size=1000)
            
            self.logger.debug(f"📝 Inserted {len(readings)} readings")
            
        except Exception as e:
            self.logger.error(f"Database insert error: {e}")
            # Attempt to reconnect
            self.reconnect_database()
    
    def reconnect_database(self):
        """Attempt to reconnect to the database"""
        try:
            if self.db_connection:
                self.db_connection.close()
            self.init_database()
            self.logger.info("🔄 Database reconnected")
        except Exception as e:
            self.logger.error(f"Failed to reconnect to database: {e}")
    
    def run(self):
        """Main monitoring loop"""
        if not self.init_sensor():
            return False
        
        if not self.init_database():
            return False
        
        self.running = True
        sample_rate = 1.0 / self.read_interval
        self.logger.info(f"🚀 Starting solar monitoring")
        info_msg = (f"📊 Sample rate: {sample_rate:.1f} Hz "
                   f"(interval: {self.read_interval}s)")
        self.logger.info(info_msg)
        self.logger.info("Press Ctrl+C to stop...")
        
        reading_count = 0
        last_status_time = time.time()
        
        try:
            while self.running:
                start_time = time.time()
                
                # Read sensor
                reading = self.read_sensor()
                if reading:
                    self.readings_buffer.append(reading)
                    reading_count += 1
                
                # Insert batch when buffer is full
                if len(self.readings_buffer) >= self.batch_size:
                    self.insert_readings_batch(self.readings_buffer)
                    self.readings_buffer.clear()
                
                # Status update every 10 seconds
                current_time = time.time()
                if current_time - last_status_time >= 10:
                    rate = reading_count / (current_time - last_status_time)
                    buffer_size = len(self.readings_buffer)
                    voltage = reading.voltage if reading else 0
                    current_ma = reading.current * 1000 if reading else 0
                    power_mw = reading.power * 1000 if reading else 0
                    energy = reading.energy if reading else 0
                    status_msg = (
                        f"📊 Status: {reading_count} samples, "
                        f"{rate:.1f} Hz | Buffer: {buffer_size} | "
                        f"V: {voltage:.3f}V, I: {current_ma:.1f}mA, "
                        f"P: {power_mw:.1f}mW, E: {energy:.3f}J"
                    )
                    self.logger.info(status_msg)
                    reading_count = 0
                    last_status_time = current_time
                
                # Maintain read interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.read_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        
        finally:
            # Insert any remaining readings
            if self.readings_buffer:
                self.insert_readings_batch(self.readings_buffer)
            
            # Close connections
            if self.db_connection:
                self.db_connection.close()
            
            self.logger.info("🛑 Solar monitoring stopped")
            return True


def main():
    """Main entry point"""
    logger = SolarDataLogger()
    success = logger.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
