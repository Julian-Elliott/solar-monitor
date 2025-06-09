#!/usr/bin/env python3
"""
Query and analyze 1-second averaged solar data from TimescaleDB
"""

import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SolarDataQueryAvg:
    """Query averaged solar data from TimescaleDB"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('TIMESCALE_HOST'),
            'port': os.getenv('TIMESCALE_PORT'),
            'user': os.getenv('TIMESCALE_USER'),
            'password': os.getenv('TIMESCALE_PASSWORD'),
            'database': os.getenv('TIMESCALE_DATABASE')
        }
    
    def connect(self):
        """Connect to database"""
        return psycopg2.connect(**self.db_config)
    
    def latest_readings(self, limit=10):
        """Get the latest N averaged readings"""
        query = """
        SELECT 
            timestamp,
            voltage_avg,
            current_avg,
            power_avg,
            shunt_voltage_avg,
            energy_last,
            charge_last,
            sample_count
        FROM solar_readings_avg 
        ORDER BY timestamp DESC 
        LIMIT %s
        """
        
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                results = cursor.fetchall()
                
                print(f"📊 Latest {len(results)} averaged readings:")
                print("-" * 100)
                print("Timestamp           | Voltage | Current | Power  | Samples | Energy  | Charge")
                print("-" * 100)
                
                for row in results:
                    timestamp, voltage, current, power, shunt_v, energy, charge, samples = row
                    print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
                          f"{voltage:7.3f}V | {current*1000:7.1f}mA | {power*1000:6.1f}mW | "
                          f"{samples:7d} | {energy:7.3f}J | {charge:7.3f}C")
                
                return results
    
    def hourly_summary(self, hours=24):
        """Get hourly summary statistics"""
        query = """
        SELECT 
            date_trunc('hour', timestamp) as hour,
            AVG(voltage_avg) as avg_voltage,
            MIN(voltage_avg) as min_voltage,
            MAX(voltage_avg) as max_voltage,
            AVG(current_avg) as avg_current,
            MIN(current_avg) as min_current,
            MAX(current_avg) as max_current,
            AVG(power_avg) as avg_power,
            MIN(power_avg) as min_power,
            MAX(power_avg) as max_power,
            COUNT(*) as data_points,
            SUM(sample_count) as total_samples
        FROM solar_readings_avg 
        WHERE timestamp >= NOW() - INTERVAL '%s hours'
        GROUP BY date_trunc('hour', timestamp)
        ORDER BY hour DESC
        """
        
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (hours,))
                results = cursor.fetchall()
                
                print(f"📈 Hourly summary for last {hours} hours:")
                print("-" * 120)
                print("Hour                | Avg V  | Min V  | Max V  | Avg mA  | Min mA  | Max mA  | Avg mW  | Points | Samples")
                print("-" * 120)
                
                for row in results:
                    hour, avg_v, min_v, max_v, avg_i, min_i, max_i, avg_p, min_p, max_p, points, samples = row
                    print(f"{hour.strftime('%Y-%m-%d %H:00')} | "
                          f"{avg_v:6.3f} | {min_v:6.3f} | {max_v:6.3f} | "
                          f"{avg_i*1000:7.1f} | {min_i*1000:7.1f} | {max_i*1000:7.1f} | "
                          f"{avg_p*1000:7.1f} | {points:6d} | {samples:7d}")
                
                return results
    
    def daily_energy(self, days=7):
        """Get daily energy summary"""
        query = """
        SELECT 
            date_trunc('day', timestamp) as day,
            MIN(energy_last) as energy_start,
            MAX(energy_last) as energy_end,
            MAX(energy_last) - MIN(energy_last) as energy_generated,
            AVG(power_avg) as avg_power,
            MAX(power_avg) as peak_power,
            COUNT(*) as data_points
        FROM solar_readings_avg 
        WHERE timestamp >= NOW() - INTERVAL '%s days'
        GROUP BY date_trunc('day', timestamp)
        ORDER BY day DESC
        """
        
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (days,))
                results = cursor.fetchall()
                
                print(f"🔋 Daily energy summary for last {days} days:")
                print("-" * 90)
                print("Date       | Energy Gen | Avg Power | Peak Power | Data Points")
                print("-" * 90)
                
                for row in results:
                    day, e_start, e_end, e_gen, avg_p, peak_p, points = row
                    print(f"{day.strftime('%Y-%m-%d')} | "
                          f"{e_gen:10.3f}J | {avg_p*1000:9.1f}mW | {peak_p*1000:10.1f}mW | "
                          f"{points:11d}")
                
                return results
    
    def table_stats(self):
        """Get table statistics"""
        queries = {
            "total_records": "SELECT COUNT(*) FROM solar_readings_avg",
            "date_range": """
                SELECT MIN(timestamp) as first_record, MAX(timestamp) as last_record 
                FROM solar_readings_avg
            """,
            "total_samples": "SELECT SUM(sample_count) FROM solar_readings_avg",
            "avg_samples_per_second": "SELECT AVG(sample_count) FROM solar_readings_avg"
        }
        
        with self.connect() as conn:
            with conn.cursor() as cursor:
                print("📊 Database Statistics:")
                print("-" * 50)
                
                # Total records
                cursor.execute(queries["total_records"])
                total = cursor.fetchone()[0]
                print(f"Total averaged records: {total:,}")
                
                # Date range
                cursor.execute(queries["date_range"])
                first, last = cursor.fetchone()
                if first and last:
                    duration = last - first
                    print(f"Date range: {first} to {last}")
                    print(f"Duration: {duration}")
                
                # Sample statistics
                cursor.execute(queries["total_samples"])
                total_samples = cursor.fetchone()[0] or 0
                print(f"Total original samples: {total_samples:,}")
                
                cursor.execute(queries["avg_samples_per_second"])
                avg_samples = cursor.fetchone()[0] or 0
                print(f"Average samples per second: {avg_samples:.1f}")
                
                if total > 0:
                    compression_ratio = total_samples / total if total > 0 else 0
                    print(f"Data compression ratio: {compression_ratio:.1f}:1")

def main():
    """Main function with interactive menu"""
    query = SolarDataQueryAvg()
    
    while True:
        print("\n" + "="*60)
        print("🌞 Solar Monitor - Averaged Data Query")
        print("="*60)
        print("1. Latest readings (last 10)")
        print("2. Hourly summary (last 24 hours)")
        print("3. Daily energy summary (last 7 days)")
        print("4. Database statistics")
        print("5. Custom latest readings")
        print("6. Custom hourly summary")
        print("0. Exit")
        print("-" * 60)
        
        try:
            choice = input("Select option (0-6): ").strip()
            
            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                query.latest_readings(10)
            elif choice == "2":
                query.hourly_summary(24)
            elif choice == "3":
                query.daily_energy(7)
            elif choice == "4":
                query.table_stats()
            elif choice == "5":
                try:
                    limit = int(input("How many latest readings? "))
                    query.latest_readings(limit)
                except ValueError:
                    print("❌ Please enter a valid number")
            elif choice == "6":
                try:
                    hours = int(input("How many hours? "))
                    query.hourly_summary(hours)
                except ValueError:
                    print("❌ Please enter a valid number")
            else:
                print("❌ Invalid option")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
