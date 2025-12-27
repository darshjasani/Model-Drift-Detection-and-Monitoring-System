"""Monitoring API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.schemas import DriftReportResponse, MetricsTimeSeriesResponse
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/drift/latest")
async def get_latest_drift_report(
    hours: Optional[int] = Query(default=1, description="Time window in hours"),
    db: Session = Depends(get_db)
):
    """
    Get latest drift detection report
    
    - **hours**: Time window to analyze (default: 1 hour)
    """
    try:
        service = MonitoringService(db)
        report = await service.get_drift_report(hours=hours)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate drift report: {str(e)}")


@router.get("/metrics/timeseries")
async def get_metrics_timeseries(
    start: Optional[str] = Query(default=None, description="Start time (ISO format)"),
    end: Optional[str] = Query(default=None, description="End time (ISO format)"),
    interval: Optional[str] = Query(default="1h", description="Time interval"),
    db: Session = Depends(get_db)
):
    """
    Get time series metrics
    
    - **start**: Start time (ISO format, default: 24 hours ago)
    - **end**: End time (ISO format, default: now)
    - **interval**: Time interval (e.g., "1h", "15m")
    """
    try:
        # Parse times
        if end is None:
            end_time = datetime.utcnow()
        else:
            end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        if start is None:
            start_time = end_time - timedelta(hours=24)
        else:
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
        
        service = MonitoringService(db)
        data = await service.get_metrics_timeseries(
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/health")
async def get_system_health(db: Session = Depends(get_db)):
    """Get system health status"""
    from app.models import SystemHealth
    from sqlalchemy import desc
    
    try:
        # Get latest health records
        health_records = db.query(SystemHealth).order_by(
            desc(SystemHealth.timestamp)
        ).limit(5).all()
        
        if not health_records:
            return {
                'status': 'unknown',
                'components': []
            }
        
        components = []
        for record in health_records:
            components.append({
                'component': record.component,
                'status': record.status,
                'timestamp': record.timestamp,
                'memory_usage': record.memory_usage
            })
        
        overall_status = 'healthy'
        if any(c['status'] != 'healthy' for c in components):
            overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'components': components,
            'timestamp': datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

