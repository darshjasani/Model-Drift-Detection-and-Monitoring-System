"""Application Configuration"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://mluser:mlpassword@localhost:5432/ml_monitoring"
    )
    
    # Model
    MODEL_PATH: str = os.getenv("MODEL_PATH", "./models")
    MODEL_VERSION: str = "xgb_v1.0.0"
    
    # Monitoring
    DRIFT_WINDOW_HOURS: int = int(os.getenv("DRIFT_WINDOW_HOURS", "1"))
    PSI_THRESHOLD: float = float(os.getenv("PSI_THRESHOLD", "0.25"))
    KS_THRESHOLD: float = float(os.getenv("KS_THRESHOLD", "0.05"))
    PERFORMANCE_DEGRADATION_THRESHOLD: float = 0.05
    
    # API
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    API_TITLE: str = "ML Drift Detection API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Production ML monitoring with drift detection"
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://frontend:3000"
    ]
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

