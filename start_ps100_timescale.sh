#!/bin/bash
# PS100 TimescaleDB Monitor Startup Script

cd "$(dirname "$0")"

echo "🌞 Starting PS100 TimescaleDB Monitor..."

# Load environment variables
source .env

# Activate virtual environment
source venv/bin/activate

# Check TimescaleDB connection
echo "🔍 Testing TimescaleDB connection..."
python3 -c "
from ps100_timescaledb import PS100TimescaleDB
try:
    db = PS100TimescaleDB()
    print('✅ TimescaleDB connection OK')
    db.close()
except Exception as e:
    print(f'❌ TimescaleDB connection failed: {e}')
    exit(1)
"

# Check if service is running
if systemctl is-active --quiet ps100-timescale-monitor; then
    echo "📋 Service is already running"
    echo "   Status: sudo systemctl status ps100-timescale-monitor"
    echo "   Logs: sudo journalctl -u ps100-timescale-monitor -f"
else
    echo "🔄 Starting PS100 TimescaleDB monitor..."
    python3 ps100_timescale_monitor.py
fi
