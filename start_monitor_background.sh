#!/bin/bash
# Start PS100 Monitor in background

# Kill any existing monitor processes
pkill -f ps100_monitor.py

# Wait a moment
sleep 2

# Start in background with nohup
cd /home/julianelliott/solar-monitor
nohup python3 ps100_monitor.py > ps100_monitor.log 2>&1 &

echo "PS100 Monitor started in background"
echo "PID: $!"
echo "Log file: /home/julianelliott/solar-monitor/ps100_monitor.log"
echo ""
echo "To check status: tail -f ps100_monitor.log"
echo "To stop: pkill -f ps100_monitor.py"
