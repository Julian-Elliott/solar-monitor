#!/bin/bash
# Quick PS100 Test Script (TimescaleDB)

cd "$(dirname "$0")"

echo "🧪 PS100 Quick Test - TimescaleDB"
echo "=================================="

# Test TimescaleDB connection
echo "1️⃣ Testing TimescaleDB connection..."
source ../../config/.env
python3 -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv('../../config/.env')
try:
    conn = psycopg2.connect(
        host=os.getenv('TIMESCALE_HOST'),
        port=os.getenv('TIMESCALE_PORT'), 
        user=os.getenv('TIMESCALE_USER'),
        password=os.getenv('TIMESCALE_PASSWORD'),
        database=os.getenv('TIMESCALE_DATABASE')
    )
    print('✅ TimescaleDB OK')
    conn.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
    exit(1)
"

# Test sensor reading
echo "2️⃣ Testing sensor reading..."
python3 ../../ps100_monitor.py --test

echo "✅ Quick test complete!"
