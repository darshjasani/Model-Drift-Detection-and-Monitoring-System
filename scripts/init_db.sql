-- ML Drift Detection Database Schema
-- Optimized for 8GB RAM systems

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Model Registry
CREATE TABLE IF NOT EXISTS model_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version VARCHAR(50) UNIQUE NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    training_date TIMESTAMP NOT NULL,
    training_samples INTEGER NOT NULL,
    feature_count INTEGER NOT NULL,
    metrics JSONB,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on version and status
CREATE INDEX idx_model_version ON model_registry(version);
CREATE INDEX idx_model_status ON model_registry(status);

-- Predictions table (partitioned by date for performance)
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    features JSONB NOT NULL,
    prediction INTEGER NOT NULL,
    prediction_proba FLOAT NOT NULL,
    feature_contributions JSONB,
    prediction_timestamp TIMESTAMP NOT NULL,
    latency_ms FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_predictions_timestamp ON predictions(prediction_timestamp DESC);
CREATE INDEX idx_predictions_model_version ON predictions(model_version);
CREATE INDEX idx_predictions_transaction_id ON predictions(transaction_id);

-- Ground Truth / Feedback
CREATE TABLE IF NOT EXISTS ground_truth (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id VARCHAR(100) NOT NULL,
    actual_label INTEGER NOT NULL,
    label_source VARCHAR(50),
    feedback_timestamp TIMESTAMP NOT NULL,
    confidence VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES predictions(transaction_id)
);

CREATE INDEX idx_ground_truth_transaction ON ground_truth(transaction_id);
CREATE INDEX idx_ground_truth_timestamp ON ground_truth(feedback_timestamp DESC);

-- Feature Statistics (Baseline and Current)
CREATE TABLE IF NOT EXISTS feature_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    statistics_type VARCHAR(20) NOT NULL, -- 'baseline' or 'current'
    time_window_start TIMESTAMP,
    time_window_end TIMESTAMP,
    mean FLOAT,
    std FLOAT,
    min FLOAT,
    max FLOAT,
    percentile_25 FLOAT,
    percentile_50 FLOAT,
    percentile_75 FLOAT,
    distribution JSONB, -- histogram data
    sample_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feature_stats_name ON feature_statistics(feature_name);
CREATE INDEX idx_feature_stats_type ON feature_statistics(statistics_type);
CREATE INDEX idx_feature_stats_window ON feature_statistics(time_window_start, time_window_end);

-- Drift Reports
CREATE TABLE IF NOT EXISTS drift_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_timestamp TIMESTAMP NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    time_window_start TIMESTAMP NOT NULL,
    time_window_end TIMESTAMP NOT NULL,
    total_predictions INTEGER NOT NULL,
    overall_status VARCHAR(20) NOT NULL, -- 'healthy', 'warning', 'critical'
    data_drift_detected BOOLEAN,
    concept_drift_detected BOOLEAN,
    performance_degraded BOOLEAN,
    feature_drift_details JSONB,
    prediction_drift JSONB,
    performance_metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_drift_reports_timestamp ON drift_reports(report_timestamp DESC);
CREATE INDEX idx_drift_reports_status ON drift_reports(overall_status);

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL, -- 'data_drift', 'concept_drift', 'performance_degradation'
    severity VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    feature_name VARCHAR(100),
    metric_value FLOAT,
    threshold_value FLOAT,
    recommendation TEXT,
    triggered_at TIMESTAMP NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_triggered ON alerts(triggered_at DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_status ON alerts(acknowledged, resolved);

-- Metrics History (Time Series)
CREATE TABLE IF NOT EXISTS metrics_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    predictions_count INTEGER NOT NULL,
    labels_received INTEGER,
    accuracy FLOAT,
    precision_score FLOAT,
    recall_score FLOAT,
    f1_score FLOAT,
    auc_roc FLOAT,
    avg_psi FLOAT,
    max_psi FLOAT,
    avg_ks_statistic FLOAT,
    drift_alerts_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_history_timestamp ON metrics_history(timestamp DESC);
CREATE INDEX idx_metrics_history_model ON metrics_history(model_version);

-- System Health
CREATE TABLE IF NOT EXISTS system_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP NOT NULL,
    component VARCHAR(50) NOT NULL, -- 'api', 'worker', 'database'
    status VARCHAR(20) NOT NULL, -- 'healthy', 'degraded', 'down'
    cpu_usage FLOAT,
    memory_usage FLOAT,
    request_rate FLOAT,
    error_rate FLOAT,
    latency_p50 FLOAT,
    latency_p95 FLOAT,
    latency_p99 FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_health_timestamp ON system_health(timestamp DESC);
CREATE INDEX idx_system_health_component ON system_health(component);

-- Create a function to clean old data (retention policy)
CREATE OR REPLACE FUNCTION clean_old_data(retention_days INTEGER DEFAULT 7)
RETURNS void AS $$
BEGIN
    -- Delete old predictions (keep last N days)
    DELETE FROM predictions 
    WHERE prediction_timestamp < NOW() - INTERVAL '1 day' * retention_days;
    
    -- Delete old drift reports
    DELETE FROM drift_reports 
    WHERE report_timestamp < NOW() - INTERVAL '1 day' * retention_days;
    
    -- Delete old metrics history
    DELETE FROM metrics_history 
    WHERE timestamp < NOW() - INTERVAL '1 day' * retention_days;
    
    -- Delete resolved alerts older than retention
    DELETE FROM alerts 
    WHERE resolved = TRUE 
    AND resolved_at < NOW() - INTERVAL '1 day' * retention_days;
    
    -- Delete old system health records
    DELETE FROM system_health 
    WHERE timestamp < NOW() - INTERVAL '1 day' * retention_days;
END;
$$ LANGUAGE plpgsql;

-- Insert initial system health record
INSERT INTO system_health (timestamp, component, status) 
VALUES (CURRENT_TIMESTAMP, 'database', 'healthy');

-- Create view for quick health check
CREATE OR REPLACE VIEW v_system_health AS
SELECT 
    m.model_version,
    m.timestamp as last_metric_time,
    m.predictions_count,
    m.accuracy,
    m.auc_roc,
    m.max_psi,
    COUNT(DISTINCT a.id) as open_alerts
FROM metrics_history m
LEFT JOIN alerts a ON a.resolved = FALSE
WHERE m.timestamp > NOW() - INTERVAL '1 hour'
GROUP BY m.model_version, m.timestamp, m.predictions_count, m.accuracy, m.auc_roc, m.max_psi
ORDER BY m.timestamp DESC
LIMIT 1;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'ML Drift Detection database initialized successfully!';
END $$;

