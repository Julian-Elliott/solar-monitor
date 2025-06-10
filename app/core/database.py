"""
Database connection and utilities
"""

import asyncpg
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    """Database connection manager"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("✅ Database connection pool created")
            
            # Ensure tables exist
            await self._create_tables()
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Database connection pool closed")
    
    async def _create_tables(self):
        """Create necessary tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Panels table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS panels (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL,
                    model TEXT DEFAULT 'PS100',
                    rated_power REAL DEFAULT 100.0,
                    i2c_address INTEGER DEFAULT 64,
                    location TEXT,
                    installation_date TIMESTAMPTZ DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # Enhanced readings table (upgrade from existing ps100_readings)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    panel_id UUID REFERENCES panels(id) ON DELETE CASCADE,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    voltage REAL NOT NULL,
                    current REAL NOT NULL,
                    power REAL NOT NULL,
                    temperature REAL,
                    efficiency REAL,
                    conditions TEXT,
                    alerts JSONB DEFAULT '[]'::jsonb,
                    shunt_voltage REAL,
                    raw_data JSONB
                )
            """)
            
            # Create hypertable for time-series data
            try:
                await conn.execute("SELECT create_hypertable('readings', 'timestamp', if_not_exists => TRUE)")
                logger.info("✅ Hypertable created for readings")
            except Exception as e:
                logger.info(f"Hypertable may already exist: {e}")
            
            # Create indexes for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_panel_id ON readings(panel_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp DESC)")
            
            logger.info("✅ Database tables initialized")

# Global database instance
database = Database()

async def get_database() -> Database:
    """Dependency to get database instance"""
    return database
