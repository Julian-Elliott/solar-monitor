#!/bin/bash

# Raspberry Pi Virtual Environment Setup Script for Solar Monitor
# This script sets up the virtual environment and installs required packages

echo "🔧 Setting up Solar Monitor environment on Raspberry Pi..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev python3-setuptools

# Enable I2C (required for INA228 sensor)
echo "🔌 Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🚀 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install Python packages
echo "📚 Installing Python packages..."
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To activate the environment manually, run:"
echo "source .venv/bin/activate"
echo ""
echo "To test the INA228 sensor, make sure:"
echo "1. I2C is enabled (reboot if first time setup)"
echo "2. INA228 is connected to GPIO pins 2 (SDA) and 3 (SCL)"
echo "3. Run: python3 -c 'import board; import adafruit_ina228; print(\"INA228 ready!\")'"
