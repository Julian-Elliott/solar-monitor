#!/bin/bash
# PS100 Solar Monitor Startup Script

cd "$(dirname "$0")"

echo "🌞 Starting PS100 Solar Monitor..."

# Activate virtual environment
source venv/bin/activate

# Check if service is running
if systemctl is-active --quiet ps100-monitor; then
    echo "📋 Service is already running"
    echo "   Use: sudo systemctl status ps100-monitor"
    echo "   Logs: sudo journalctl -u ps100-monitor -f"
else
    echo "🔄 Starting PS100 monitor..."
    python3 ps100_monitor.py
fi
