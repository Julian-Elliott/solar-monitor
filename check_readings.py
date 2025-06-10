#!/usr/bin/env python3
"""
Quick script to check readings in the database directly
"""

import asyncio
import asyncpg
import os
from datetime import datetime

async def check_readings():
    # Database connection from environment
    DATABASE_URL = (
        f"postgresql://{os.getenv('TIMESCALE_USER', 'postgres')}:"
        f"{os.getenv('TIMESCALE_PASSWORD', 'password')}@"
        f"{os.getenv('TIMESCALE_HOST', 'localhost')}:"
        f"{os.getenv('TIMESCALE_PORT', '5432')}/"
        f"{os.getenv('TIMESCALE_DATABASE', 'ps100_monitor')}"
    )
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Check total count
        total_count = await conn.fetchval("SELECT COUNT(*) FROM readings")
        print(f"Total readings in database: {total_count}")
        
        # Check count by panel
        panel_counts = await conn.fetch("""
            SELECT panel_id, COUNT(*) as count 
            FROM readings 
            GROUP BY panel_id 
            ORDER BY count DESC
        """)
        
        print("\nReadings per panel:")
        for row in panel_counts:
            print(f"  Panel {row['panel_id']}: {row['count']} readings")
        
        # Check recent readings (last 10)
        recent = await conn.fetch("""
            SELECT id, panel_id, timestamp, power 
            FROM readings 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        print(f"\nLast 10 readings:")
        for row in recent:
            print(f"  {row['timestamp']}: Panel {row['panel_id']} - {row['power']:.2f}W")
            
        # Check if new readings are being added
        latest_time = await conn.fetchval("SELECT MAX(timestamp) FROM readings")
        print(f"\nLatest reading timestamp: {latest_time}")
        
        if latest_time:
            age = datetime.utcnow() - latest_time.replace(tzinfo=None)
            print(f"Age of latest reading: {age.total_seconds():.1f} seconds")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_readings())
