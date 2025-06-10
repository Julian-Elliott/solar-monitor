#!/usr/bin/env python3
"""
Solar Monitor Data Logger - 1-Second Average Mode
Continuously reads INA228 sensor data at high frequency but stores 1-second averages in TimescaleDB
Reduces database storage while maintaining statistical accuracy
"""

import os
import time
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass
from statistics import mean
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
    """Data class for individual sensor readings"""
    timestamp: datetime
    voltage: float
    current: float
    power: float
    shunt_voltage: float
    energy: float
    charge: float

@dataclass
class AveragedReading:
    """Data class for averaged sensor readings"""
    timestamp: datetime  # Rounded to the second
    voltage_avg: float
    current_avg: float
    power_avg: float
    shunt_voltage_avg: float
    energy_last: float  # Use last value for cumulative energy
    charge_last: float  # Use last value for cumulative charge
    sample_count: int   # Number of samples averaged

class SolarDataLoggerAveraged:
    """Solar data logger that stores 1-second averages"""
    
    def __init__(self):
        self.setup_logging()
        self.sensor = None
        self.db_connection = None
        self.running = False
        
        # Averaging buffers
        self.current_second_readings: List[SensorReading] = []
        self.last_second_timestamp = None
        
        # Configuration from environment
        self.read_interval = float(os.getenv('SENSOR_READ_INTERVAL', 0.1))  # High frequency sampling
        
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
                logging.FileHandler('solar_monitor_avg.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def init_sensor(self):
        """Initialize the INA228 sensor"""
        try:
            self.logger.info("Initializing INA228 sensor...")
            i2c = board.I2C()
            self.sensor = adafruit_ina228.INA228(i2c)
            
            # Apply solar monitoring calibration fix
            apply_solar_calibration(self.sensor)
            self.logger.info("🔧 Applied solar monitoring calibration (0.1Ω, 1A)")
            
            # Log sensor information
            self.logger.info(f"✅ INA228 connected successfully!")
            self.logger.info(f"📋 Averaging: {self.sensor.averaging_count} samples")
            self.logger.info(f"📋 Current voltage: {self.sensor.bus_voltage:.3f}V")
            self.logger.info(f"📋 Current: {self.sensor.current*1000:.1f}mA")
            
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
        """Create the solar data table and hypertable for averaged data"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS solar_readings_avg (
            timestamp TIMESTAMPTZ NOT NULL,
            voltage_avg DOUBLE PRECISION NOT NULL,
            current_avg DOUBLE PRECISION NOT NULL,
            power_avg DOUBLE PRECISION NOT NULL,
            shunt_voltage_avg DOUBLE PRECISION NOT NULL,
            energy_last DOUBLE PRECISION NOT NULL,
            charge_last DOUBLE PRECISION NOT NULL,
            sample_count INTEGER NOT NULL
        );
        """
        
        # Create hypertable for time-series optimization
        hypertable_sql = """
        SELECT create_hypertable('solar_readings_avg', 'timestamp', if_not_exists => TRUE);
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
                energy=self.sensor.energy,
                charge=self.sensor.charge
            )
            
            return reading
            
        except Exception as e:
            self.logger.error(f"Error reading sensor: {e}")
            raise
    
    def get_second_timestamp(self, dt: datetime) -> datetime:
        """Get timestamp rounded down to the second"""
        return dt.replace(microsecond=0)
    
    def process_second_data(self, readings: List[SensorReading]) -> AveragedReading:
        """Process a list of readings and return averaged data"""
        if not readings:
            return None
        
        # Calculate averages
        voltage_avg = mean(r.voltage for r in readings)
        current_avg = mean(r.current for r in readings)
        power_avg = mean(r.power for r in readings)
        shunt_voltage_avg = mean(r.shunt_voltage for r in readings)
        
        # Use last values for cumulative measurements
        energy_last = readings[-1].energy
        charge_last = readings[-1].charge
        
        # Get the second timestamp
        second_timestamp = self.get_second_timestamp(readings[0].timestamp)
        
        return AveragedReading(
            timestamp=second_timestamp,
            voltage_avg=voltage_avg,
            current_avg=current_avg,
            power_avg=power_avg,
            shunt_voltage_avg=shunt_voltage_avg,
            energy_last=energy_last,
            charge_last=charge_last,
            sample_count=len(readings)
        )
    
    def insert_averaged_reading(self, avg_reading: AveragedReading):
        """Insert an averaged reading into the database"""
        insert_sql = """
        INSERT INTO solar_readings_avg 
        (timestamp, voltage_avg, current_avg, power_avg, shunt_voltage_avg, 
         energy_last, charge_last, sample_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        data = (
            avg_reading.timestamp,
            avg_reading.voltage_avg,
            avg_reading.current_avg,
            avg_reading.power_avg,
            avg_reading.shunt_voltage_avg,
            avg_reading.energy_last,
            avg_reading.charge_last,
            avg_reading.sample_count
        )
        
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute(insert_sql, data)
            
            self.logger.debug(f"📝 Inserted 1-second average ({avg_reading.sample_count} samples)")
            
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
        self.logger.info(f"🚀 Starting solar monitoring with 1-second averaging")
        self.logger.info(f"📊 Sample rate: {sample_rate:.1f} Hz (interval: {self.read_interval}s)")
        self.logger.info("Press Ctrl+C to stop...")
        
        reading_count = 0
        last_status_time = time.time()
        
        try:
            while self.running:
                start_time = time.time()
                
                # Read sensor
                reading = self.read_sensor()
                reading_count += 1
                
                # Get the current second timestamp
                current_second = self.get_second_timestamp(reading.timestamp)
                
                # Check if we're in a new second
                if self.last_second_timestamp is None:
                    self.last_second_timestamp = current_second
                
                if current_second != self.last_second_timestamp:
                    # Process and store the previous second's data
                    if self.current_second_readings:
                        avg_reading = self.process_second_data(self.current_second_readings)
                        if avg_reading:
                            self.insert_averaged_reading(avg_reading)
                    
                    # Start new second
                    self.current_second_readings = []
                    self.last_second_timestamp = current_second
                
                # Add reading to current second buffer
                self.current_second_readings.append(reading)
                
                # Status update every 10 seconds
                current_time = time.time()
                if current_time - last_status_time >= 10:
                    rate = reading_count / (current_time - last_status_time)
                    buffer_size = len(self.current_second_readings)
                    self.logger.info(
                        f"📊 Status: {reading_count} samples, {rate:.1f} Hz | Buffer: {buffer_size} | "
                        f"V: {reading.voltage:.3f}V, I: {reading.current*1000:.1f}mA, "
                        f"P: {reading.power*1000:.1f}mW"
                    )
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
            # Process any remaining readings
            if self.current_second_readings:
                avg_reading = self.process_second_data(self.current_second_readings)
                if avg_reading:
                    self.insert_averaged_reading(avg_reading)
            
            # Close connections
            if self.db_connection:
                self.db_connection.close()
            
            self.logger.info("🛑 Solar monitoring stopped")
            return True

def main():
    """Main entry point"""
    logger = SolarDataLoggerAveraged()
    success = logger.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
