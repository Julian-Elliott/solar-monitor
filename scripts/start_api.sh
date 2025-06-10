#!/bin/bash
# SolarScope Pro API Startup Script

set -e

echo "🚀 Starting SolarScope Pro API..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if config exists
if [ ! -f "config/.env" ]; then
    echo "❌ Configuration file config/.env not found!"
    echo "   Please create it with your TimescaleDB settings."
    exit 1
fi

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run database migrations/setup if needed
echo "🗄️  Setting up database..."
python -c "
import asyncio
from app.core.database import database

async def setup():
    await database.connect()
    print('✅ Database setup completed')
    await database.disconnect()

asyncio.run(setup())
"

# Start the API server
echo "🌐 Starting FastAPI server..."
echo "📍 API will be available at: http://localhost:8000"
echo "📚 API docs will be available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
