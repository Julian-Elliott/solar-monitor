#!/usr/bin/env python3
"""
Database setup and test script for TimescaleDB
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test the connection to TimescaleDB"""
    db_config = {
        'host': os.getenv('TIMESCALE_HOST'),
        'port': os.getenv('TIMESCALE_PORT'),
        'user': os.getenv('TIMESCALE_USER'),
        'password': os.getenv('TIMESCALE_PASSWORD'),
        'database': os.getenv('TIMESCALE_DATABASE')
    }
    
    print("🔌 Testing TimescaleDB connection...")
    print(f"   Host: {db_config['host']}:{db_config['port']}")
    print(f"   Database: {db_config['database']}")
    print(f"   User: {db_config['user']}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**db_config)
        print("✅ Database connection successful!")
        
        # Test TimescaleDB extension
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"📊 PostgreSQL version: {version}")
            
            cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';")
            result = cursor.fetchone()
            if result:
                print(f"⏰ TimescaleDB version: {result[1]}")
            else:
                print("⚠️  TimescaleDB extension not found")
            
            # Show existing tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            if tables:
                print(f"📋 Existing tables: {', '.join([t[0] for t in tables])}")
            else:
                print("📋 No tables found in public schema")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    """Main function"""
    success = test_database_connection()
    if success:
        print("\n🎉 Database setup complete! Ready to run data_logger.py")
    else:
        print("\n❌ Database setup failed. Check your configuration in .env file")

if __name__ == "__main__":
    main()
