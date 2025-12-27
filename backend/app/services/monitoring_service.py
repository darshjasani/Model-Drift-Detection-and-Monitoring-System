"""Monitoring Service - Calculate metrics and detect drift"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
import numpy as np
import logging

from app.models import (
    Prediction, GroundTruth, DriftReport, Alert,
    MetricsHistory, FeatureStatistics
)
from app.ml.drift_detector import DriftDetector
from app.config import settings

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring model performance and drift"""
    
    def __init__(self, db: Session):
        """Initialize monitoring service"""
        self.db = db
        self.drift_detector = DriftDetector(
            psi_threshold=settings.PSI_THRESHOLD,
            ks_threshold=settings.KS_THRESHOLD
        )
    
    async def get_drift_report(
        self,
        hours: int = None
    ) -> Dict:
        """
        Generate comprehensive drift report
        
        Args:
            hours: Time window in hours (default: from config)
            
        Returns:
            Drift report dictionary
        """
        if hours is None:
            hours = settings.DRIFT_WINDOW_HOURS
        
        try:
            # Get time window
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Get baseline data (from training or first week)
            baseline_df = self._get_baseline_features()
            
            # Get current data
            current_df = self._get_current_features(start_time, end_time)
            
            if len(current_df) == 0:
                return self._empty_report(start_time, end_time)
            
            # Detect feature drift
            feature_drift_reports = self.drift_detector.detect_feature_drift(
                baseline_df,
                current_df
            )
            
            # Detect prediction drift
            baseline_predictions = baseline_df.index.to_series().apply(lambda x: 0.02)  # Baseline fraud rate
            current_predictions = self._get_predictions(start_time, end_time)
            
            prediction_drift = None
            if len(current_predictions) > 0:
                baseline_pred_array = np.full(len(current_predictions), 0.02)
                prediction_drift = self.drift_detector.detect_prediction_drift(
                    baseline_pred_array,
                    current_predictions
                )
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(start_time, end_time)
            
            # Determine overall status
            data_drift_detected = any(
                r['status'] == 'drifted' for r in feature_drift_reports
            )
            
            concept_drift_detected = (
                prediction_drift and prediction_drift['status'] == 'drifted'
            ) if prediction_drift else False
            
            high_severity_count = sum(
                1 for r in feature_drift_reports if r['severity'] == 'high'
            )
            
            if high_severity_count >= 2:
                overall_status = 'critical'
            elif data_drift_detected or concept_drift_detected:
                overall_status = 'warning'
            else:
                overall_status = 'healthy'
            
            # Generate alerts
            alerts = self._generate_alerts(feature_drift_reports, prediction_drift)
            
            # Build report
            report = {
                'report_timestamp': datetime.utcnow(),
                'time_window': f"{start_time.isoformat()} to {end_time.isoformat()}",
                'total_predictions': len(current_df),
                'model_version': settings.MODEL_VERSION,
                'overall_status': {
                    'health': overall_status,
                    'data_drift_detected': data_drift_detected,
                    'concept_drift_detected': concept_drift_detected,
                    'performance_degraded': False
                },
                'feature_drift': feature_drift_reports,
                'prediction_drift': prediction_drift,
                'performance_metrics': performance_metrics,
                'alerts': alerts
            }
            
            # Store report in database
            self._store_drift_report(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating drift report: {e}", exc_info=True)
            raise
    
    async def get_metrics_timeseries(
        self,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1h"
    ) -> Dict:
        """
        Get time series metrics
        
        Args:
            start_time: Start time
            end_time: End time
            interval: Time interval (e.g., "1h", "15m")
            
        Returns:
            Time series data
        """
        try:
            # Query metrics history
            metrics = self.db.query(MetricsHistory).filter(
                MetricsHistory.timestamp >= start_time,
                MetricsHistory.timestamp <= end_time
            ).order_by(MetricsHistory.timestamp).all()
            
            data_points = []
            for metric in metrics:
                data_points.append({
                    'timestamp': metric.timestamp,
                    'predictions_count': metric.predictions_count,
                    'labels_received': metric.labels_received,
                    'accuracy': metric.accuracy,
                    'precision': metric.precision_score,
                    'recall': metric.recall_score,
                    'auc_roc': metric.auc_roc,
                    'avg_psi': metric.avg_psi,
                    'max_psi': metric.max_psi,
                    'drift_alerts': metric.drift_alerts_count
                })
            
            return {
                'interval': interval,
                'start_time': start_time,
                'end_time': end_time,
                'data_points': data_points
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics timeseries: {e}")
            raise
    
    def _get_baseline_features(self) -> pd.DataFrame:
        """Get baseline feature statistics"""
        # For simplicity, use first 10000 predictions as baseline
        # In production, this would be stored during training
        predictions = self.db.query(Prediction).limit(10000).all()
        
        if not predictions:
            # Return synthetic baseline if no predictions yet
            from app.ml.data_generator import SyntheticDataGenerator
            generator = SyntheticDataGenerator()
            X, _ = generator.generate_baseline_data(1000)
            return X
        
        # Extract features
        features_list = [p.features for p in predictions]
        df = pd.DataFrame(features_list)
        
        return df
    
    def _get_current_features(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Get current feature data"""
        predictions = self.db.query(Prediction).filter(
            Prediction.prediction_timestamp >= start_time,
            Prediction.prediction_timestamp <= end_time
        ).all()
        
        if not predictions:
            return pd.DataFrame()
        
        features_list = [p.features for p in predictions]
        df = pd.DataFrame(features_list)
        
        return df
    
    def _get_predictions(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> np.ndarray:
        """Get prediction probabilities"""
        predictions = self.db.query(Prediction.prediction_proba).filter(
            Prediction.prediction_timestamp >= start_time,
            Prediction.prediction_timestamp <= end_time
        ).all()
        
        return np.array([p[0] for p in predictions])
    
    def _calculate_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """Calculate performance metrics (when ground truth is available)"""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        try:
            # Query predictions with ground truth
            results = self.db.query(
                Prediction.prediction,
                Prediction.prediction_proba,
                GroundTruth.actual_label
            ).join(
                GroundTruth,
                Prediction.transaction_id == GroundTruth.transaction_id
            ).filter(
                Prediction.prediction_timestamp >= start_time,
                Prediction.prediction_timestamp <= end_time
            ).all()
            
            if not results:
                return {
                    'accuracy': None,
                    'precision': None,
                    'recall': None,
                    'f1_score': None,
                    'auc_roc': None
                }
            
            y_pred = np.array([r[0] for r in results])
            y_proba = np.array([r[1] for r in results])
            y_true = np.array([r[2] for r in results])
            
            metrics = {
                'accuracy': float(accuracy_score(y_true, y_pred)),
                'precision': float(precision_score(y_true, y_pred, zero_division=0)),
                'recall': float(recall_score(y_true, y_pred, zero_division=0)),
                'f1_score': float(f1_score(y_true, y_pred, zero_division=0)),
                'auc_roc': float(roc_auc_score(y_true, y_proba)) if len(np.unique(y_true)) > 1 else None
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {
                'accuracy': None,
                'precision': None,
                'recall': None,
                'f1_score': None,
                'auc_roc': None
            }
    
    def _generate_alerts(
        self,
        feature_drift_reports: List[Dict],
        prediction_drift: Optional[Dict]
    ) -> List[Dict]:
        """Generate alerts from drift reports"""
        alerts = []
        
        for report in feature_drift_reports:
            if report['severity'] in ['high', 'medium']:
                alert = {
                    'id': f"alert_{hash(report['feature_name']) % 10000}",
                    'type': 'data_drift',
                    'severity': report['severity'],
                    'message': (
                        f"Feature '{report['feature_name']}' has "
                        f"PSI={report['drift_score']:.2f} "
                        f"(threshold={report['threshold']})"
                    ),
                    'triggered_at': datetime.utcnow(),
                    'recommendation': self._get_recommendation(report)
                }
                alerts.append(alert)
        
        return alerts
    
    def _get_recommendation(self, drift_report: Dict) -> str:
        """Get recommendation for drift"""
        if drift_report['severity'] == 'high':
            return (
                f"Investigate {drift_report['feature_name']} data pipeline. "
                f"Consider retraining model."
            )
        elif drift_report['severity'] == 'medium':
            return f"Monitor {drift_report['feature_name']} closely. Plan retraining."
        else:
            return "Continue monitoring."
    
    def _store_drift_report(self, report: Dict):
        """Store drift report in database"""
        try:
            # Implementation would store the report
            # Skipping for brevity
            pass
        except Exception as e:
            logger.error(f"Error storing drift report: {e}")
    
    def _empty_report(self, start_time: datetime, end_time: datetime) -> Dict:
        """Return empty report when no data"""
        return {
            'report_timestamp': datetime.utcnow(),
            'time_window': f"{start_time.isoformat()} to {end_time.isoformat()}",
            'total_predictions': 0,
            'model_version': settings.MODEL_VERSION,
            'overall_status': {
                'health': 'unknown',
                'data_drift_detected': False,
                'concept_drift_detected': False,
                'performance_degraded': False
            },
            'feature_drift': [],
            'prediction_drift': None,
            'performance_metrics': {},
            'alerts': []
        }

