#!/usr/bin/env python3
"""
Query script to view solar monitoring data from TimescaleDB
"""

import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def connect_db():
    """Connect to the database"""
    db_config = {
        'host': os.getenv('TIMESCALE_HOST'),
        'port': os.getenv('TIMESCALE_PORT'),
        'user': os.getenv('TIMESCALE_USER'),
        'password': os.getenv('TIMESCALE_PASSWORD'),
        'database': os.getenv('TIMESCALE_DATABASE')
    }
    return psycopg2.connect(**db_config)

def show_recent_data(hours=1, limit=20):
    """Show recent solar data"""
    print(f"📊 Showing last {limit} readings from the past {hours} hour(s)...")
    
    conn = connect_db()
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                timestamp,
                voltage,
                current * 1000 as current_ma,
                power * 1000 as power_mw,
                temperature
            FROM solar_readings 
            WHERE timestamp >= NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC 
            LIMIT %s
        """, (hours, limit))
        
        rows = cursor.fetchall()
        
        if not rows:
            print("No data found in the specified time range")
            return
        
        print("\nTimestamp                  Voltage   Current    Power    Temp")
        print("-" * 65)
        
        for row in rows:
            timestamp, voltage, current_ma, power_mw, temperature = row
            print(f"{timestamp:%Y-%m-%d %H:%M:%S} {voltage:7.3f}V {current_ma:7.1f}mA {power_mw:7.1f}mW {temperature:5.1f}°C")
    
    conn.close()

def show_statistics(hours=24):
    """Show statistical summary"""
    print(f"\n📈 Statistics for the past {hours} hour(s)...")
    
    conn = connect_db()
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                COUNT(*) as readings_count,
                MIN(voltage) as min_voltage,
                MAX(voltage) as max_voltage,
                AVG(voltage) as avg_voltage,
                MIN(current * 1000) as min_current_ma,
                MAX(current * 1000) as max_current_ma,
                AVG(current * 1000) as avg_current_ma,
                MIN(power * 1000) as min_power_mw,
                MAX(power * 1000) as max_power_mw,
                AVG(power * 1000) as avg_power_mw,
                MIN(temperature) as min_temp,
                MAX(temperature) as max_temp,
                AVG(temperature) as avg_temp
            FROM solar_readings 
            WHERE timestamp >= NOW() - INTERVAL '%s hours'
        """, (hours,))
        
        row = cursor.fetchone()
        
        if row[0] == 0:
            print("No data found in the specified time range")
            return
        
        count, min_v, max_v, avg_v, min_i, max_i, avg_i, min_p, max_p, avg_p, min_t, max_t, avg_t = row
        
        print(f"Total readings: {count}")
        print(f"Voltage:  Min: {min_v:.3f}V, Max: {max_v:.3f}V, Avg: {avg_v:.3f}V")
        print(f"Current:  Min: {min_i:.1f}mA, Max: {max_i:.1f}mA, Avg: {avg_i:.1f}mA")
        print(f"Power:    Min: {min_p:.1f}mW, Max: {max_p:.1f}mW, Avg: {avg_p:.1f}mW")
        print(f"Temp:     Min: {min_t:.1f}°C, Max: {max_t:.1f}°C, Avg: {avg_t:.1f}°C")
    
    conn.close()

def main():
    """Main function"""
    try:
        show_recent_data(hours=1, limit=10)
        show_statistics(hours=24)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
