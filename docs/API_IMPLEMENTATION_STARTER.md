# SolarScope Pro - API Implementation Starter

## 🚀 Let's Build the API Layer First

This will give us:
- **Modern REST API** for all functionality
- **Real-time WebSocket** connections
- **Authentication & Authorization**
- **Foundation for web dashboard**

### Step 1: Project Restructure
```bash
# Rename to product name
mv solar-monitor solarscope-pro
cd solarscope-pro

# Create new structure
mkdir -p app/{api,core,models,services,utils}
mkdir -p tests/{unit,integration}
mkdir -p docker
```

### Step 2: FastAPI Setup
```python
# app/main.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import panels, readings, alerts
from app.core.config import settings

app = FastAPI(
    title="SolarScope Pro API",
    description="Professional Solar Panel Monitoring Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(panels.router, prefix="/api/v1")
app.include_router(readings.router, prefix="/api/v1") 
app.include_router(alerts.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "SolarScope Pro API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

### Step 3: Enhanced Data Models
```python
# app/models/panel.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4

class PanelBase(BaseModel):
    name: str = Field(..., description="Panel display name")
    model: str = Field(default="PS100", description="Panel model")
    rated_power: float = Field(default=100.0, ge=0, description="Rated power in watts")
    i2c_address: int = Field(default=0x40, description="I2C sensor address")
    location: Optional[str] = Field(None, description="Installation location")

class PanelCreate(PanelBase):
    pass

class Panel(PanelBase):
    id: UUID = Field(default_factory=uuid4)
    installation_date: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    last_reading: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# app/models/reading.py
class ReadingBase(BaseModel):
    voltage: float = Field(..., ge=0, description="Voltage in volts")
    current: float = Field(..., ge=0, description="Current in amperes") 
    power: float = Field(..., ge=0, description="Power in watts")
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    efficiency: float = Field(..., ge=0, le=200, description="Efficiency percentage")

class Reading(ReadingBase):
    id: UUID = Field(default_factory=uuid4)
    panel_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    conditions: str = Field(..., description="Solar conditions assessment")
    alerts: List[str] = Field(default=[], description="Active alerts")
```

### Step 4: API Routes
```python
# app/api/routes/panels.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models.panel import Panel, PanelCreate
from app.services.panel_service import PanelService

router = APIRouter(prefix="/panels", tags=["panels"])

@router.get("/", response_model=List[Panel])
async def list_panels(panel_service: PanelService = Depends()):
    """Get all solar panels"""
    return await panel_service.get_all()

@router.post("/", response_model=Panel)
async def create_panel(panel: PanelCreate, panel_service: PanelService = Depends()):
    """Add a new solar panel"""
    return await panel_service.create(panel)

@router.get("/{panel_id}", response_model=Panel)
async def get_panel(panel_id: UUID, panel_service: PanelService = Depends()):
    """Get specific panel details"""
    panel = await panel_service.get_by_id(panel_id)
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found")
    return panel

@router.delete("/{panel_id}")
async def delete_panel(panel_id: UUID, panel_service: PanelService = Depends()):
    """Remove a solar panel"""
    success = await panel_service.delete(panel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Panel not found")
    return {"message": "Panel deleted successfully"}

# Real-time WebSocket endpoint
@router.websocket("/{panel_id}/live")
async def panel_live_data(websocket: WebSocket, panel_id: UUID):
    """WebSocket for real-time panel data"""
    await websocket.accept()
    try:
        while True:
            # Get latest reading for panel
            reading = await panel_service.get_latest_reading(panel_id)
            await websocket.send_json(reading.dict())
            await asyncio.sleep(1)  # Send updates every second
    except WebSocketDisconnect:
        pass
```

### Step 5: Business Logic Services
```python
# app/services/panel_service.py
from typing import List, Optional
from uuid import UUID
from app.models.panel import Panel, PanelCreate
from app.models.reading import Reading
from app.core.database import get_database

class PanelService:
    def __init__(self):
        self.db = get_database()
    
    async def get_all(self) -> List[Panel]:
        """Get all registered panels"""
        # Implementation with TimescaleDB
        pass
    
    async def create(self, panel_data: PanelCreate) -> Panel:
        """Register a new panel"""
        # Implementation
        pass
    
    async def get_by_id(self, panel_id: UUID) -> Optional[Panel]:
        """Get panel by ID"""
        # Implementation
        pass
    
    async def get_latest_reading(self, panel_id: UUID) -> Optional[Reading]:
        """Get most recent reading for panel"""
        # Implementation
        pass

# app/services/monitoring_service.py
class MonitoringService:
    """Core monitoring logic - enhanced from current PS100Monitor"""
    
    def __init__(self):
        self.panels = {}
        self.sensors = {}
        self.database = get_database()
    
    async def start_monitoring(self):
        """Start continuous monitoring of all panels"""
        # Enhanced version of current monitoring loop
        pass
    
    async def add_panel(self, panel: Panel):
        """Add panel to monitoring"""
        # Initialize sensor and add to monitoring loop
        pass
    
    async def remove_panel(self, panel_id: UUID):
        """Remove panel from monitoring"""
        pass
```

### Step 6: Configuration Management
```python
# app/core/config.py
from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    api_title: str = "SolarScope Pro"
    api_version: str = "1.0.0"
    debug: bool = False
    
    # Database Configuration  
    timescale_host: str = Field(..., env="TIMESCALE_HOST")
    timescale_port: int = Field(5432, env="TIMESCALE_PORT")
    timescale_user: str = Field(..., env="TIMESCALE_USER")
    timescale_password: str = Field(..., env="TIMESCALE_PASSWORD")
    timescale_database: str = Field(..., env="TIMESCALE_DATABASE")
    
    # Monitoring Configuration
    scan_interval: float = Field(1.0, description="Sensor scan interval in seconds")
    max_panels: int = Field(100, description="Maximum number of panels")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = "config/.env"

settings = Settings()
```

### Step 7: Docker Setup
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TIMESCALE_HOST=timescale
      - TIMESCALE_PORT=5432
      - TIMESCALE_USER=postgres
      - TIMESCALE_PASSWORD=password
      - TIMESCALE_DATABASE=solarscope
      - SECRET_KEY=your-secret-key-here
    volumes:
      - .:/app
    depends_on:
      - timescale
  
  timescale:
    image: timescale/timescaledb:latest-pg14
    environment:
      - POSTGRES_DB=solarscope
      - POSTGRES_USER=postgres  
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data

volumes:
  timescale_data:
```

## 🎯 **Implementation Order**

1. **Setup FastAPI** (`app/main.py`)
2. **Create data models** (`app/models/`)
3. **Build API routes** (`app/api/routes/`)
4. **Migrate monitoring logic** (`app/services/`)
5. **Add Docker support**
6. **Create web dashboard**

## 🚀 **Ready to Start?**

This gives us:
- ✅ **Professional API** with auto-generated docs
- ✅ **Real-time WebSocket** connections
- ✅ **Scalable architecture** for growth
- ✅ **Easy deployment** with Docker
- ✅ **Foundation** for web interface

**Next**: Would you like me to start implementing the FastAPI setup and begin migrating the current monitoring code into this new structure?
