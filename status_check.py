#!/usr/bin/env python3
"""
Solar Monitor Status Check
Shows the current system status and configuration
"""

import os
import sys
import subprocess
from pathlib import Path

def check_file_exists(filename, description):
    """Check if a file exists"""
    exists = Path(filename).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filename}")
    return exists

def check_venv():
    """Check virtual environment"""
    venv_path = Path(".venv")
    if venv_path.exists():
        print("✅ Virtual environment: .venv/")
        # Check if it's activated
        if sys.prefix != sys.base_prefix:
            print("✅ Virtual environment is activated")
        else:
            print("⚠️  Virtual environment exists but not activated")
            print("   Run: source .venv/bin/activate")
        return True
    else:
        print("❌ Virtual environment: Not found")
        print("   Run: ./setup.sh")
        return False

def check_i2c():
    """Check I2C configuration"""
    try:
        # Check if I2C is enabled
        result = subprocess.run(['lsmod'], capture_output=True, text=True)
        if 'i2c_dev' in result.stdout:
            print("✅ I2C kernel module loaded")
        else:
            print("❌ I2C kernel module not loaded")
            return False
        
        # Check for I2C devices
        result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ I2C bus accessible")
            if '40' in result.stdout:
                print("✅ INA228 sensor detected at address 0x40")
            else:
                print("⚠️  INA228 sensor not detected")
        else:
            print("❌ I2C bus not accessible")
            return False
        
        return True
    except FileNotFoundError:
        print("❌ I2C tools not available")
        return False

def check_env_config():
    """Check environment configuration"""
    env_file = Path(".env")
    if env_file.exists():
        print("✅ Configuration file: .env")
        
        # Check for required variables
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = [
            'TIMESCALE_HOST', 'TIMESCALE_PORT', 'TIMESCALE_USER',
            'TIMESCALE_PASSWORD', 'TIMESCALE_DATABASE'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
            return False
        else:
            print("✅ All required environment variables set")
            return True
    else:
        print("❌ Configuration file: .env not found")
        print("   Copy from .env.example and edit with your credentials")
        return False

def main():
    """Main status check"""
    print("🌞 Solar Monitor - System Status Check")
    print("=" * 50)
    
    # Check files
    print("\n📁 Files:")
    files_ok = True
    files_ok &= check_file_exists("setup.sh", "Setup script")
    files_ok &= check_file_exists("data_logger.py", "Data logger")
    files_ok &= check_file_exists("requirements.txt", "Requirements")
    files_ok &= check_file_exists(".env.example", "Example config")
    
    # Check virtual environment
    print("\n🐍 Virtual Environment:")
    venv_ok = check_venv()
    
    # Check I2C (only on Raspberry Pi)
    print("\n🔌 I2C Hardware:")
    try:
        i2c_ok = check_i2c()
    except:
        print("ℹ️  I2C check skipped (not on Raspberry Pi)")
        i2c_ok = True
    
    # Check configuration
    print("\n⚙️  Configuration:")
    config_ok = True
    try:
        config_ok = check_env_config()
    except ImportError:
        print("⚠️  python-dotenv not installed (run pip install -r requirements.txt)")
        config_ok = False
    
    # Overall status
    print("\n" + "=" * 50)
    if files_ok and venv_ok and config_ok:
        print("🎉 System ready! You can start data logging with:")
        print("   ./start_logger.sh")
    else:
        print("⚠️  System needs attention. Please fix the issues above.")
        if not venv_ok:
            print("   1. Run: ./setup.sh")
        if not config_ok:
            print("   2. Edit .env file with your database credentials")
        if not i2c_ok:
            print("   3. Enable I2C: sudo raspi-config")

if __name__ == "__main__":
    main()
