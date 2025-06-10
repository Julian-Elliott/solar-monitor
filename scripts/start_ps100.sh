#!/bin/bash
# PS100 Solar Monitor Startup Script (TimescaleDB)

cd "$(dirname "$0")"

echo "🌞 Starting PS100 Solar Monitor..."

# Load environment variables
source ../config/.env

# Check TimescaleDB connection
echo "🔍 Testing TimescaleDB connection..."
python3 -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
try:
    conn = psycopg2.connect(
        host=os.getenv('TIMESCALE_HOST'),
        port=os.getenv('TIMESCALE_PORT'),
        user=os.getenv('TIMESCALE_USER'),
        password=os.getenv('TIMESCALE_PASSWORD'),
        database=os.getenv('TIMESCALE_DATABASE')
    )
    print('✅ TimescaleDB connection OK')
    conn.close()
except Exception as e:
    print(f'❌ TimescaleDB connection failed: {e}')
    exit(1)
"

# Check if service is running
if systemctl is-active --quiet ps100-timescale-monitor; then
    echo "📋 Service is already running"
    echo "   Use: sudo systemctl status ps100-timescale-monitor"
    echo "   Logs: sudo journalctl -u ps100-timescale-monitor -f"
else
    echo "🔄 Starting PS100 monitor..."
    python3 ../ps100_monitor.py
fi
