"""SQLAlchemy Database Models"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.database import Base


class ModelRegistry(Base):
    """Model Registry - Track deployed models"""
    
    __tablename__ = "model_registry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(50), unique=True, nullable=False, index=True)
    model_type = Column(String(50), nullable=False)
    training_date = Column(DateTime, nullable=False)
    training_samples = Column(Integer, nullable=False)
    feature_count = Column(Integer, nullable=False)
    metrics = Column(JSONB)
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, default=func.now())


class Prediction(Base):
    """Predictions made by the model"""
    
    __tablename__ = "predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    model_version = Column(String(50), nullable=False, index=True)
    features = Column(JSONB, nullable=False)
    prediction = Column(Integer, nullable=False)
    prediction_proba = Column(Float, nullable=False)
    feature_contributions = Column(JSONB)
    prediction_timestamp = Column(DateTime, nullable=False, index=True)
    latency_ms = Column(Float)
    created_at = Column(DateTime, default=func.now())


# Create composite index for time-based queries
Index('idx_predictions_time_model', 
      Prediction.prediction_timestamp.desc(), 
      Prediction.model_version)


class GroundTruth(Base):
    """Ground truth labels (delayed feedback)"""
    
    __tablename__ = "ground_truth"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(100), ForeignKey('predictions.transaction_id'), nullable=False, index=True)
    actual_label = Column(Integer, nullable=False)
    label_source = Column(String(50))
    feedback_timestamp = Column(DateTime, nullable=False, index=True)
    confidence = Column(String(20))
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())


class FeatureStatistics(Base):
    """Feature statistics for drift detection"""
    
    __tablename__ = "feature_statistics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_name = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=False)
    statistics_type = Column(String(20), nullable=False, index=True)  # 'baseline' or 'current'
    time_window_start = Column(DateTime, index=True)
    time_window_end = Column(DateTime, index=True)
    mean = Column(Float)
    std = Column(Float)
    min = Column(Float)
    max = Column(Float)
    percentile_25 = Column(Float)
    percentile_50 = Column(Float)
    percentile_75 = Column(Float)
    distribution = Column(JSONB)  # Histogram
    sample_count = Column(Integer)
    created_at = Column(DateTime, default=func.now())


Index('idx_feature_stats_window', 
      FeatureStatistics.time_window_start, 
      FeatureStatistics.time_window_end)


class DriftReport(Base):
    """Drift detection reports"""
    
    __tablename__ = "drift_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_timestamp = Column(DateTime, nullable=False, index=True)
    model_version = Column(String(50), nullable=False)
    time_window_start = Column(DateTime, nullable=False)
    time_window_end = Column(DateTime, nullable=False)
    total_predictions = Column(Integer, nullable=False)
    overall_status = Column(String(20), nullable=False, index=True)
    data_drift_detected = Column(Boolean)
    concept_drift_detected = Column(Boolean)
    performance_degraded = Column(Boolean)
    feature_drift_details = Column(JSONB)
    prediction_drift = Column(JSONB)
    performance_metrics = Column(JSONB)
    created_at = Column(DateTime, default=func.now())


class Alert(Base):
    """System alerts"""
    
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    feature_name = Column(String(100))
    metric_value = Column(Float)
    threshold_value = Column(Float)
    recommendation = Column(Text)
    triggered_at = Column(DateTime, nullable=False, index=True)
    acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_at = Column(DateTime)
    resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


Index('idx_alerts_status', Alert.acknowledged, Alert.resolved)


class MetricsHistory(Base):
    """Time series metrics"""
    
    __tablename__ = "metrics_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, index=True)
    model_version = Column(String(50), nullable=False, index=True)
    predictions_count = Column(Integer, nullable=False)
    labels_received = Column(Integer)
    accuracy = Column(Float)
    precision_score = Column(Float)
    recall_score = Column(Float)
    f1_score = Column(Float)
    auc_roc = Column(Float)
    avg_psi = Column(Float)
    max_psi = Column(Float)
    avg_ks_statistic = Column(Float)
    drift_alerts_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())


class SystemHealth(Base):
    """System health monitoring"""
    
    __tablename__ = "system_health"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, index=True)
    component = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    request_rate = Column(Float)
    error_rate = Column(Float)
    latency_p50 = Column(Float)
    latency_p95 = Column(Float)
    latency_p99 = Column(Float)
    created_at = Column(DateTime, default=func.now())

