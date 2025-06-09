#!/bin/bash

# Install Solar Monitor Averaged Logger as a systemd service

echo "🔧 Installing Solar Monitor Averaged Logger as a system service..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please run this script as a regular user (not sudo)"
    echo "   The script will prompt for sudo when needed"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "data_logger_avg.py" ]; then
    echo "❌ Error: Please run this script from the solar-monitor directory"
    exit 1
fi

# Get current directory and user
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo "📁 Project directory: $CURRENT_DIR"
echo "👤 User: $CURRENT_USER"

# Update the service file with correct paths and user
sed -e "s|/home/pi/solar-monitor|$CURRENT_DIR|g" \
    -e "s|User=pi|User=$CURRENT_USER|g" \
    -e "s|Group=pi|Group=$CURRENT_USER|g" \
    solar-monitor-avg.service > /tmp/solar-monitor-avg.service

# Copy service file to systemd directory
echo "📋 Installing averaged logger service file..."
sudo cp /tmp/solar-monitor-avg.service /etc/systemd/system/

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable the service
echo "✅ Enabling solar-monitor-avg service..."
sudo systemctl enable solar-monitor-avg.service

echo ""
echo "🎉 Averaged logger service installed successfully!"
echo ""
echo "Service commands:"
echo "  Start:   sudo systemctl start solar-monitor-avg"
echo "  Stop:    sudo systemctl stop solar-monitor-avg"
echo "  Status:  sudo systemctl status solar-monitor-avg"
echo "  Logs:    sudo journalctl -u solar-monitor-avg -f"
echo ""
echo "The service will automatically start on boot."
echo "To start it now, run: sudo systemctl start solar-monitor-avg"
