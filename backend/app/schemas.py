"""Pydantic Schemas for Request/Response Validation"""

from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


# ============================================================================
# PREDICTION SCHEMAS
# ============================================================================

class PredictionRequest(BaseModel):
    """Request schema for making predictions"""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    features: Dict[str, Any] = Field(..., description="Feature dictionary")
    timestamp: Optional[datetime] = Field(default=None, description="Request timestamp")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "transaction_id": "txn_1234567890",
            "features": {
                "amount": 127.50,
                "hour_of_day": 14,
                "distance_from_home_km": 5.2,
                "merchant_risk_score": 0.15
            },
            "timestamp": "2025-12-26T14:32:15Z"
        }
    })


class PredictionResponse(BaseModel):
    """Response schema for predictions"""
    transaction_id: str
    prediction: int
    prediction_label: str
    confidence: float
    fraud_probability: float
    model_version: str
    model_trained_at: datetime
    prediction_timestamp: datetime
    latency_ms: float
    feature_contributions: Optional[Dict[str, float]] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# FEEDBACK / GROUND TRUTH SCHEMAS
# ============================================================================

class FeedbackRequest(BaseModel):
    """Request schema for submitting ground truth"""
    transaction_id: str
    actual_label: int = Field(..., ge=0, le=1, description="Actual label (0 or 1)")
    label_source: Optional[str] = Field(default="manual", description="Source of the label")
    feedback_timestamp: Optional[datetime] = Field(default=None)
    confidence: Optional[str] = Field(default="high", description="Confidence in label")
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response schema for feedback submission"""
    status: str
    transaction_id: str
    prediction_was_correct: bool
    metrics_updated: bool
    current_accuracy_24h: Optional[float] = None


# ============================================================================
# DRIFT DETECTION SCHEMAS
# ============================================================================

class FeatureDriftDetail(BaseModel):
    """Drift details for a single feature"""
    feature_name: str
    drift_score: float
    drift_method: str
    threshold: float
    status: str  # 'stable', 'drifted'
    severity: str  # 'none', 'low', 'medium', 'high'
    baseline_stats: Dict[str, float]
    current_stats: Dict[str, float]
    distribution_shift: Optional[Dict[str, float]] = None


class PredictionDrift(BaseModel):
    """Prediction distribution drift"""
    method: str
    statistic: float
    p_value: float
    threshold: float
    status: str
    baseline_fraud_rate: float
    current_fraud_rate: float
    change_pct: float


class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_roc: Optional[float] = None
    baseline_comparison: Optional[Dict[str, float]] = None


class DriftAlert(BaseModel):
    """Drift alert"""
    id: str
    type: str
    severity: str
    message: str
    triggered_at: datetime
    recommendation: Optional[str] = None


class DriftReportResponse(BaseModel):
    """Complete drift report response"""
    report_timestamp: datetime
    time_window: str
    total_predictions: int
    model_version: str
    overall_status: Dict[str, Any]
    feature_drift: List[FeatureDriftDetail]
    prediction_drift: Optional[PredictionDrift] = None
    performance_metrics: PerformanceMetrics
    alerts: List[DriftAlert]


# ============================================================================
# METRICS SCHEMAS
# ============================================================================

class MetricsDataPoint(BaseModel):
    """Single metrics data point for time series"""
    timestamp: datetime
    predictions_count: int
    labels_received: Optional[int] = None
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    auc_roc: Optional[float] = None
    avg_psi: Optional[float] = None
    max_psi: Optional[float] = None
    drift_alerts: int = 0


class MetricsTimeSeriesResponse(BaseModel):
    """Time series metrics response"""
    interval: str
    start_time: datetime
    end_time: datetime
    data_points: List[MetricsDataPoint]


# ============================================================================
# MODEL REGISTRY SCHEMAS
# ============================================================================

class ModelInfo(BaseModel):
    """Model information"""
    version: str
    model_type: str
    trained_at: datetime
    training_samples: int
    features_count: int
    status: str
    metrics: Optional[Dict[str, float]] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class HealthStatus(BaseModel):
    """System health status"""
    overall: str  # 'healthy', 'warning', 'critical'
    data_quality: str
    performance: str
    drift: str


class LiveMetrics(BaseModel):
    """Live metrics for dashboard"""
    requests_per_second: float
    avg_latency_ms: float
    accuracy_24h: Optional[float] = None
    auc_24h: Optional[float] = None
    predictions_today: int


class AlertsSummary(BaseModel):
    """Summary of alerts by severity"""
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class DashboardOverview(BaseModel):
    """Dashboard overview data"""
    model_info: ModelInfo
    health_status: HealthStatus
    live_metrics: LiveMetrics
    alerts_summary: AlertsSummary


# ============================================================================
# WEBSOCKET SCHEMAS
# ============================================================================

class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str  # 'metrics_update', 'alert', 'drift_detected'
    timestamp: datetime
    data: Dict[str, Any]


# ============================================================================
# SIMULATOR SCHEMAS
# ============================================================================

class DriftConfig(BaseModel):
    """Configuration for drift injection"""
    enabled: bool = True
    feature_shifts: Optional[Dict[str, Dict[str, Any]]] = None
    concept_drift: Optional[Dict[str, Any]] = None


class SimulatorStatus(BaseModel):
    """Traffic simulator status"""
    status: str  # 'running', 'stopped'
    current_rps: int
    total_requests_sent: int
    drift_active: bool
    active_drifts: List[Dict[str, Any]]

