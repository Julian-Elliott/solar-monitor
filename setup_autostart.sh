#!/bin/bash
# Add this line to /etc/rc.local (before exit 0) to start monitoring on boot:
# /home/julianelliott/solar-monitor/start_monitor_background.sh

# Or add to crontab with: @reboot /home/julianelliott/solar-monitor/start_monitor_background.sh

echo "Setting up PS100 Monitor to start on boot..."

# Add to crontab
(crontab -l 2>/dev/null; echo "@reboot sleep 30 && /home/julianelliott/solar-monitor/start_monitor_background.sh") | crontab -

echo "✅ PS100 Monitor will now start automatically on boot"
echo "✅ Current monitoring is running in background"
