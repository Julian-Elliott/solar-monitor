#!/bin/bash
# PS100 Solar Monitor Startup Script (Unified)

cd "$(dirname "$0")"

echo "🌞 Starting PS100 Solar Monitor (Unified)..."

# Activate virtual environment
source venv/bin/activate

# Check if service is running
if systemctl is-active --quiet ps100-timescale-monitor; then
    echo "📋 Service is already running"
    echo "   Use: sudo systemctl status ps100-timescale-monitor"
    echo "   Logs: sudo journalctl -u ps100-timescale-monitor -f"
else
    echo "🔄 Starting PS100 monitor (SQLite mode)..."
    python3 ps100.py
fi
