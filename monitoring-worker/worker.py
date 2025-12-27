"""Background Monitoring Worker - Calculate Metrics and Detect Drift"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mluser:mlpassword@postgres:5432/ml_monitoring"
)

MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "30"))  # seconds


class MonitoringWorker:
    """Background worker for monitoring and drift detection"""
    
    def __init__(self):
        """Initialize worker"""
        self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info("Monitoring worker initialized")
    
    def run_monitoring_cycle(self):
        """Run one monitoring cycle"""
        logger.info("=" * 60)
        logger.info("Starting monitoring cycle...")
        start_time = time.time()
        
        session = self.SessionLocal()
        try:
            # Calculate and store metrics
            self._calculate_metrics(session)
            
            # Check for drift
            self._check_drift(session)
            
            # Update system health
            self._update_system_health(session)
            
            session.commit()
            
            elapsed = time.time() - start_time
            logger.info(f"Monitoring cycle completed in {elapsed:.2f}s")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()
    
    def _calculate_metrics(self, session):
        """Calculate and store current metrics"""
        from sqlalchemy import text
        
        try:
            # Get counts for last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            # Count predictions
            result = session.execute(
                text("""
                    SELECT COUNT(*) as pred_count
                    FROM predictions
                    WHERE prediction_timestamp >= :time_threshold
                """),
                {"time_threshold": one_hour_ago}
            ).fetchone()
            
            predictions_count = result[0] if result else 0
            
            # Count ground truth labels
            result = session.execute(
                text("""
                    SELECT COUNT(*) as label_count
                    FROM ground_truth
                    WHERE feedback_timestamp >= :time_threshold
                """),
                {"time_threshold": one_hour_ago}
            ).fetchone()
            
            labels_count = result[0] if result else 0
            
            # Calculate accuracy if we have labels
            accuracy = None
            if labels_count > 0:
                result = session.execute(
                    text("""
                        SELECT 
                            SUM(CASE WHEN p.prediction = g.actual_label THEN 1 ELSE 0 END)::float / COUNT(*) as accuracy
                        FROM predictions p
                        JOIN ground_truth g ON p.transaction_id = g.transaction_id
                        WHERE p.prediction_timestamp >= :time_threshold
                    """),
                    {"time_threshold": one_hour_ago}
                ).fetchone()
                
                accuracy = float(result[0]) if result and result[0] else None
            
            # Store metrics
            session.execute(
                text("""
                    INSERT INTO metrics_history 
                    (timestamp, model_version, predictions_count, labels_received, accuracy)
                    VALUES (:timestamp, :model_version, :pred_count, :label_count, :accuracy)
                """),
                {
                    "timestamp": datetime.utcnow(),
                    "model_version": os.getenv("MODEL_VERSION", "xgb_v1.0.0"),
                    "pred_count": predictions_count,
                    "label_count": labels_count,
                    "accuracy": accuracy
                }
            )
            
            logger.info(f"Metrics calculated: predictions={predictions_count}, "
                       f"labels={labels_count}, accuracy={accuracy}")
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
    
    def _check_drift(self, session):
        """Check for drift in features and predictions"""
        try:
            # Simple drift check - count predictions in last hour vs baseline
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            from sqlalchemy import text
            result = session.execute(
                text("""
                    SELECT AVG(prediction_proba) as avg_proba
                    FROM predictions
                    WHERE prediction_timestamp >= :time_threshold
                """),
                {"time_threshold": one_hour_ago}
            ).fetchone()
            
            if result and result[0]:
                avg_proba = float(result[0])
                baseline_fraud_rate = 0.02  # 2% baseline
                
                # Check if significantly different
                if abs(avg_proba - baseline_fraud_rate) > 0.03:
                    logger.warning(f"Prediction drift detected! "
                                 f"Current fraud rate: {avg_proba:.4f}, "
                                 f"Baseline: {baseline_fraud_rate:.4f}")
                    
                    # Create alert
                    session.execute(
                        text("""
                            INSERT INTO alerts 
                            (alert_type, severity, title, message, triggered_at)
                            VALUES (:type, :severity, :title, :message, :triggered_at)
                        """),
                        {
                            "type": "prediction_drift",
                            "severity": "medium",
                            "title": "Prediction Distribution Drift",
                            "message": f"Average fraud probability shifted from {baseline_fraud_rate:.4f} to {avg_proba:.4f}",
                            "triggered_at": datetime.utcnow()
                        }
                    )
                else:
                    logger.info(f"No significant drift detected. Fraud rate: {avg_proba:.4f}")
            
        except Exception as e:
            logger.error(f"Error checking drift: {e}")
    
    def _update_system_health(self, session):
        """Update system health metrics"""
        from sqlalchemy import text
        import psutil
        
        try:
            # Get system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Store health record
            session.execute(
                text("""
                    INSERT INTO system_health 
                    (timestamp, component, status, cpu_usage, memory_usage)
                    VALUES (:timestamp, :component, :status, :cpu_usage, :memory_usage)
                """),
                {
                    "timestamp": datetime.utcnow(),
                    "component": "monitoring_worker",
                    "status": "healthy",
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage
                }
            )
            
            logger.info(f"System health: CPU={cpu_usage:.1f}%, Memory={memory_usage:.1f}%")
            
        except Exception as e:
            logger.error(f"Error updating system health: {e}")
    
    def start(self):
        """Start the monitoring worker"""
        logger.info("=" * 60)
        logger.info("ML Drift Detection - Monitoring Worker")
        logger.info("=" * 60)
        logger.info(f"Monitoring interval: {MONITORING_INTERVAL} seconds")
        logger.info(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")
        logger.info("=" * 60)
        
        # Run initial cycle after a short delay
        time.sleep(10)
        self.run_monitoring_cycle()
        
        # Schedule regular monitoring
        schedule.every(MONITORING_INTERVAL).seconds.do(self.run_monitoring_cycle)
        
        logger.info("Worker started. Running monitoring cycles...")
        
        # Run scheduled tasks
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Monitoring worker stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(5)


if __name__ == "__main__":
    worker = MonitoringWorker()
    worker.start()

