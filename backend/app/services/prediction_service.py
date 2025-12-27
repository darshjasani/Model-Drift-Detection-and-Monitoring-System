"""Prediction Service - Handle predictions and storage"""

from datetime import datetime
from typing import Dict, Tuple
from sqlalchemy.orm import Session
import logging
import uuid

from app.ml.model import get_model
from app.models import Prediction, ModelRegistry
from app.config import settings

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for making predictions and storing results"""
    
    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.db = db
        self.model = get_model()
    
    async def make_prediction(
        self,
        transaction_id: str,
        features: Dict[str, float],
        timestamp: datetime = None
    ) -> Dict:
        """
        Make prediction and store in database
        
        Args:
            transaction_id: Unique transaction ID
            features: Feature dictionary
            timestamp: Prediction timestamp
            
        Returns:
            Prediction result dictionary
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        try:
            # Make prediction
            prediction, probability, contributions, latency = self.model.predict(
                features,
                compute_contributions=True
            )
            
            # Store in database
            db_prediction = Prediction(
                transaction_id=transaction_id,
                model_version=self.model.version,
                features=features,
                prediction=prediction,
                prediction_proba=probability,
                feature_contributions=contributions,
                prediction_timestamp=timestamp,
                latency_ms=latency
            )
            
            self.db.add(db_prediction)
            self.db.commit()
            
            # Prepare response
            result = {
                'transaction_id': transaction_id,
                'prediction': prediction,
                'prediction_label': 'fraud' if prediction == 1 else 'legitimate',
                'confidence': 1 - probability if prediction == 0 else probability,
                'fraud_probability': probability,
                'model_version': self.model.version,
                'model_trained_at': self.model.training_date,
                'prediction_timestamp': timestamp,
                'latency_ms': latency,
                'feature_contributions': contributions
            }
            
            logger.debug(f"Prediction made: {transaction_id} -> {prediction} (prob={probability:.4f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            self.db.rollback()
            raise
    
    async def submit_feedback(
        self,
        transaction_id: str,
        actual_label: int,
        label_source: str = "manual",
        feedback_timestamp: datetime = None,
        confidence: str = "high",
        notes: str = None
    ) -> Dict:
        """
        Submit ground truth feedback
        
        Args:
            transaction_id: Transaction ID
            actual_label: Actual label (0 or 1)
            label_source: Source of label
            feedback_timestamp: Feedback timestamp
            confidence: Confidence level
            notes: Additional notes
            
        Returns:
            Feedback result dictionary
        """
        from app.models import GroundTruth
        
        if feedback_timestamp is None:
            feedback_timestamp = datetime.utcnow()
        
        try:
            # Check if prediction exists
            prediction = self.db.query(Prediction).filter(
                Prediction.transaction_id == transaction_id
            ).first()
            
            if not prediction:
                raise ValueError(f"Prediction not found: {transaction_id}")
            
            # Store ground truth
            ground_truth = GroundTruth(
                transaction_id=transaction_id,
                actual_label=actual_label,
                label_source=label_source,
                feedback_timestamp=feedback_timestamp,
                confidence=confidence,
                notes=notes
            )
            
            self.db.add(ground_truth)
            self.db.commit()
            
            # Check if prediction was correct
            was_correct = (prediction.prediction == actual_label)
            
            # Calculate recent accuracy (optional)
            recent_accuracy = self._calculate_recent_accuracy()
            
            result = {
                'status': 'accepted',
                'transaction_id': transaction_id,
                'prediction_was_correct': was_correct,
                'metrics_updated': True,
                'current_accuracy_24h': recent_accuracy
            }
            
            logger.info(f"Feedback submitted: {transaction_id} -> {actual_label} (correct={was_correct})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            self.db.rollback()
            raise
    
    def _calculate_recent_accuracy(self, hours: int = 24) -> float:
        """Calculate accuracy for recent predictions with ground truth"""
        from app.models import GroundTruth
        from datetime import timedelta
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Query predictions with ground truth
            results = self.db.query(
                Prediction.prediction,
                GroundTruth.actual_label
            ).join(
                GroundTruth,
                Prediction.transaction_id == GroundTruth.transaction_id
            ).filter(
                Prediction.prediction_timestamp >= cutoff_time
            ).all()
            
            if not results:
                return None
            
            correct = sum(1 for pred, actual in results if pred == actual)
            accuracy = correct / len(results)
            
            return round(accuracy, 4)
            
        except Exception as e:
            logger.error(f"Error calculating recent accuracy: {e}")
            return None
    
    def get_model_info(self) -> Dict:
        """Get current model information"""
        return self.model.get_metadata()

