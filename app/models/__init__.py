"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import json

class PanelBase(BaseModel):
    """Base panel model with common fields"""
    name: str = Field(..., description="Panel display name", min_length=1, max_length=100)
    model: str = Field(default="PS100", description="Panel model")
    rated_power: float = Field(default=100.0, ge=0, le=1000, description="Rated power in watts")
    i2c_address: int = Field(default=0x40, ge=0x01, le=0x7F, description="I2C sensor address")
    location: Optional[str] = Field(None, description="Installation location", max_length=200)

class PanelCreate(PanelBase):
    """Model for creating a new panel"""
    pass

class PanelUpdate(BaseModel):
    """Model for updating panel information"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    model: Optional[str] = None
    rated_power: Optional[float] = Field(None, ge=0, le=1000)
    location: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

class Panel(PanelBase):
    """Complete panel model with database fields"""
    id: UUID
    installation_date: datetime
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_reading_time: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ReadingBase(BaseModel):
    """Base reading model"""
    voltage: float = Field(..., ge=0, le=50, description="Voltage in volts")
    current: float = Field(..., ge=0, le=20, description="Current in amperes")
    power: float = Field(..., ge=0, le=1000, description="Power in watts")
    temperature: Optional[float] = Field(None, ge=-40, le=100, description="Temperature in Celsius")
    efficiency: float = Field(..., ge=0, le=200, description="Efficiency percentage")
    conditions: str = Field(..., description="Solar conditions assessment")
    alerts: List[str] = Field(default=[], description="Active alerts")
    shunt_voltage: Optional[float] = Field(None, description="Shunt voltage for debugging")

class ReadingCreate(ReadingBase):
    """Model for creating a new reading"""
    panel_id: UUID

class Reading(ReadingBase):
    """Complete reading model with database fields"""
    id: UUID
    panel_id: UUID
    timestamp: datetime
    raw_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class ReadingResponse(BaseModel):
    """API response for readings with panel info"""
    reading: Reading
    panel: Panel

class PanelSummary(BaseModel):
    """Summary statistics for a panel"""
    panel_id: UUID
    panel_name: str
    latest_reading: Optional[Reading] = None
    daily_energy: float = Field(0.0, description="Daily energy generation in Wh")
    daily_peak_power: float = Field(0.0, description="Daily peak power in W")
    average_efficiency: float = Field(0.0, description="Average efficiency today")
    total_readings: int = Field(0, description="Total readings today")
    status: str = Field("unknown", description="Panel status")

class SystemStatus(BaseModel):
    """Overall system status"""
    total_panels: int
    active_panels: int  
    total_power: float
    system_efficiency: float
    alerts_count: int
    last_update: datetime
    uptime: str

class AlertCreate(BaseModel):
    """Model for creating alerts"""
    panel_id: UUID
    alert_type: str = Field(..., description="Type of alert")
    message: str = Field(..., description="Alert message")
    severity: str = Field(default="warning", pattern="^(info|warning|error|critical)$")
    
class Alert(BaseModel):
    """Alert model"""
    id: UUID
    panel_id: UUID
    alert_type: str
    message: str
    severity: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    is_active: bool = True

# Response models for API endpoints
class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: List[Any]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 0

    def __init__(self, **data):
        if 'pages' not in data:
            total = data.get('total', 0)
            size = data.get('size', 50)
            data['pages'] = (total + size - 1) // size if total > 0 else 0
        super().__init__(**data)
