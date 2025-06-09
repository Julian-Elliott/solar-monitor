#!/bin/bash

# Solar Monitor Startup Script
# Activates virtual environment and starts data logging

echo "🌞 Solar Monitor - Starting up..."

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the solar-monitor directory"
    exit 1
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Error: Virtual environment not found. Run ./setup.sh first"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Database configuration missing."
    exit 1
fi

# Install/update dependencies
echo "📦 Checking dependencies..."
pip install -r requirements.txt --quiet

# Test database connection first
echo "🔌 Testing database connection..."
python3 db_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🚀 Starting data logger..."
    echo "   Reading interval: 100ms (10 Hz)"
    echo "   Database: TimescaleDB at 192.168.42.125"
    echo ""
    echo "Press Ctrl+C to stop logging"
    echo ""
    
    # Start the data logger
    python3 data_logger.py
else
    echo "❌ Database connection failed. Please check your configuration."
    exit 1
fi
