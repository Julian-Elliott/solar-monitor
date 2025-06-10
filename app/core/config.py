"""
SolarScope Pro - Core Configuration
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    api_title: str = "SolarScope Pro API"
    api_version: str = "1.0.0" 
    api_description: str = "Professional Solar Panel Monitoring Platform"
    debug: bool = False
    
    # Database Configuration
    timescale_host: str = Field(..., env="TIMESCALE_HOST")
    timescale_port: int = Field(5432, env="TIMESCALE_PORT")
    timescale_user: str = Field(..., env="TIMESCALE_USER") 
    timescale_password: str = Field(..., env="TIMESCALE_PASSWORD")
    timescale_database: str = Field(..., env="TIMESCALE_DATABASE")
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.timescale_user}:{self.timescale_password}@{self.timescale_host}:{self.timescale_port}/{self.timescale_database}"
    
    # Monitoring Configuration
    scan_interval: float = Field(1.0, description="Sensor scan interval in seconds")
    max_panels: int = Field(100, description="Maximum number of panels")
    
    # Legacy sensor configuration (from old config)
    sensor_read_interval: float = Field(0.1, env="SENSOR_READ_INTERVAL", description="Sensor read interval")
    batch_insert_size: int = Field(10, env="BATCH_INSERT_SIZE", description="Batch insert size")
    log_level: str = Field("INFO", env="LOG_LEVEL", description="Logging level")
    
    # Security (for future authentication)
    secret_key: str = Field("dev-secret-key-change-in-production", env="SECRET_KEY")
    access_token_expire_minutes: int = 30
    
    # CORS Configuration
    cors_origins: list = ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        env_file = "config/.env"
        case_sensitive = False

# Global settings instance
settings = Settings()
