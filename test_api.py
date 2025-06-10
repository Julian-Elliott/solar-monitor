#!/usr/bin/env python3
"""
Test script to verify API components
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

def test_imports():
    """Test all major imports"""
    
    try:
        print("🧪 Testing Pydantic...")
        from pydantic import BaseModel
        print("✅ Pydantic OK")
    except Exception as e:
        print(f"❌ Pydantic failed: {e}")
        return False
    
    try:
        print("🧪 Testing FastAPI...")
        from fastapi import FastAPI
        print("✅ FastAPI OK")
    except Exception as e:
        print(f"❌ FastAPI failed: {e}")
        return False
        
    try:
        print("🧪 Testing models...")
        from app.models import Panel, Reading
        print("✅ Models OK")
    except Exception as e:
        print(f"❌ Models failed: {e}")
        return False
        
    try:
        print("🧪 Testing config...")
        from app.core.config import settings
        print(f"✅ Config OK - API: {settings.api_title}")
    except Exception as e:
        print(f"❌ Config failed: {e}")
        return False
        
    try:
        print("🧪 Testing services...")
        from app.services import PanelService
        print("✅ Services OK")
    except Exception as e:
        print(f"❌ Services failed: {e}")
        return False
        
    try:
        print("🧪 Testing routes...")
        from app.api.routes import panels
        print("✅ Routes OK")
    except Exception as e:
        print(f"❌ Routes failed: {e}")
        return False
        
    try:
        print("🧪 Testing main app...")
        from app.main import app
        print(f"✅ Main app OK - Title: {app.title}")
    except Exception as e:
        print(f"❌ Main app failed: {e}")
        return False
    
    print("\n🎉 All imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
