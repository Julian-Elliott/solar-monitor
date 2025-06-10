"""
SolarScope Pro - FastAPI Application
Main entry point for the solar monitoring API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn
import asyncio

from app.core.config import settings
from app.core.database import database
from app.api.routes import panels, readings, alerts, system
from app.services import sensor_integration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting SolarScope Pro API...")
    try:
        await database.connect()
        logger.info("✅ Database connected successfully")
        
        # Initialize sensor integration
        await sensor_integration.initialize()
        
        # Auto-discover and register panel sensors
        panel_count = await sensor_integration.auto_discover_panels()
        logger.info(f"📡 Registered {panel_count} panel sensors")
        
        # Start background sensor monitoring
        if panel_count > 0:
            monitoring_task = asyncio.create_task(
                sensor_integration.start_monitoring(interval=settings.scan_interval)
            )
            app.state.monitoring_task = monitoring_task
            logger.info("🔄 Background sensor monitoring started")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down SolarScope Pro API...")
    
    # Stop sensor monitoring
    sensor_integration.stop_monitoring()
    if hasattr(app.state, 'monitoring_task'):
        app.state.monitoring_task.cancel()
        try:
            await app.state.monitoring_task
        except asyncio.CancelledError:
            pass
    
    await database.disconnect()
    logger.info("✅ Database disconnected")

# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.local"]
)

# Include API routes
app.include_router(panels.router, prefix="/api/v1/panels", tags=["panels"])
app.include_router(readings.router, prefix="/api/v1/readings", tags=["readings"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to SolarScope Pro API",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/api/v1/system/health"
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        async with database.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "service": "SolarScope Pro API",
            "version": settings.api_version,
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
