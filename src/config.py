"""
PS100 Configuration and Constants
"""

from dataclasses import dataclass

@dataclass
class PS100Config:
    """PS100 panel configuration"""
    RATED_VOLTAGE = 26.5    # Vmp - Maximum Power Voltage
    RATED_CURRENT = 3.77    # Imp - Maximum Power Current  
    RATED_POWER = 100       # Watts
    SHUNT_RESISTANCE = 0.015  # 15mΩ integrated shunt
    MAX_CURRENT = 10.0      # 10A fuse rating
    MAX_VOLTAGE = 30.0      # Safety margin
