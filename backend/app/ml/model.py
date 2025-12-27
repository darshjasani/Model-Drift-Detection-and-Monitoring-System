"""ML Model Wrapper for Production Inference"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging
import time

from app.config import settings

logger = logging.getLogger(__name__)


class MLModel:
    """Production ML Model Wrapper"""
    
    def __init__(self, model_path: str = None, version: str = None):
        """
        Initialize model wrapper
        
        Args:
            model_path: Path to model directory
            version: Model version to load
        """
        self.model_path = model_path or settings.MODEL_PATH
        self.version = version or settings.MODEL_VERSION
        self.model = None
        self.metadata = None
        self.feature_names = None
        self.training_date = None
        self.is_loaded = False
        
    def load(self):
        """Load model from disk"""
        try:
            model_file = Path(self.model_path) / f"model_{self.version}.joblib"
            metadata_file = Path(self.model_path) / f"metadata_{self.version}.joblib"
            
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_file}")
            
            # Load model
            self.model = joblib.load(model_file)
            self.metadata = joblib.load(metadata_file)
            
            # Extract metadata
            self.feature_names = self.metadata['feature_names']
            self.training_date = self.metadata['training_date']
            self.is_loaded = True
            
            logger.info(f"Model loaded successfully: {self.version}")
            logger.info(f"Training date: {self.training_date}")
            logger.info(f"Features: {len(self.feature_names)}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def predict(
        self,
        features: Dict[str, float],
        compute_contributions: bool = True
    ) -> Tuple[int, float, Optional[Dict[str, float]]]:
        """
        Make prediction
        
        Args:
            features: Feature dictionary
            compute_contributions: Whether to compute feature contributions
            
        Returns:
            (prediction, probability, feature_contributions)
        """
        if not self.is_loaded:
            self.load()
        
        start_time = time.time()
        
        try:
            # Convert to DataFrame
            X = self._prepare_features(features)
            
            # Make prediction
            prediction = int(self.model.predict(X)[0])
            probability = float(self.model.predict_proba(X)[0, 1])
            
            # Calculate feature contributions (simplified SHAP-like)
            feature_contributions = None
            if compute_contributions:
                feature_contributions = self._get_feature_contributions(X)
            
            latency = (time.time() - start_time) * 1000  # ms
            
            return prediction, probability, feature_contributions, latency
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            raise
    
    def predict_batch(
        self,
        features_list: list
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make batch predictions (faster for multiple samples)
        
        Args:
            features_list: List of feature dictionaries
            
        Returns:
            (predictions, probabilities)
        """
        if not self.is_loaded:
            self.load()
        
        try:
            # Convert to DataFrame
            X = pd.DataFrame(features_list)
            X = X[self.feature_names]  # Ensure correct order
            
            # Make predictions
            predictions = self.model.predict(X)
            probabilities = self.model.predict_proba(X)[:, 1]
            
            return predictions, probabilities
            
        except Exception as e:
            logger.error(f"Error in batch prediction: {e}")
            raise
    
    def _prepare_features(self, features: Dict[str, float]) -> pd.DataFrame:
        """
        Prepare features for prediction
        
        Args:
            features: Feature dictionary
            
        Returns:
            DataFrame with correct feature order
        """
        # Check for missing features
        missing = set(self.feature_names) - set(features.keys())
        if missing:
            raise ValueError(f"Missing features: {missing}")
        
        # Create DataFrame with correct feature order
        X = pd.DataFrame([features])[self.feature_names]
        
        return X
    
    def _get_feature_contributions(self, X: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate feature contributions (simplified version)
        
        Uses feature importance * (feature_value - mean) as proxy for SHAP
        This is faster than true SHAP and good enough for monitoring
        
        Args:
            X: Feature DataFrame (single row)
            
        Returns:
            Dictionary of feature contributions
        """
        try:
            # Get feature importances
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            else:
                # Fallback to uniform importance
                importances = np.ones(len(self.feature_names)) / len(self.feature_names)
            
            # Get feature values
            feature_values = X.iloc[0].values
            
            # Simple contribution: importance * normalized_value
            # This is a proxy for SHAP values (much faster to compute)
            contributions = {}
            for i, feature in enumerate(self.feature_names):
                # Normalize by importance
                contribution = float(importances[i] * feature_values[i] / 100)  # Scale down
                contributions[feature] = round(contribution, 4)
            
            return contributions
            
        except Exception as e:
            logger.error(f"Error calculating feature contributions: {e}")
            return {}
    
    def get_metadata(self) -> Dict:
        """Get model metadata"""
        if not self.is_loaded:
            self.load()
        
        return {
            'version': self.version,
            'training_date': self.training_date,
            'feature_names': self.feature_names,
            'feature_count': len(self.feature_names),
            'model_type': self.metadata.get('model_type', 'Unknown'),
            'metrics': self.metadata.get('metrics', {})
        }
    
    def health_check(self) -> bool:
        """
        Check if model is healthy
        
        Returns:
            True if model is loaded and functional
        """
        if not self.is_loaded:
            return False
        
        try:
            # Make a dummy prediction
            dummy_features = {name: 0.0 for name in self.feature_names}
            prediction, _, _, _ = self.predict(dummy_features, compute_contributions=False)
            return True
        except:
            return False


# Global model instance (singleton)
_model_instance = None


def get_model() -> MLModel:
    """
    Get or create global model instance
    
    Returns:
        MLModel instance
    """
    global _model_instance
    
    if _model_instance is None:
        _model_instance = MLModel()
        _model_instance.load()
    
    return _model_instance


if __name__ == "__main__":
    # Test model loading and prediction
    model = MLModel()
    model.load()
    
    # Test prediction
    test_features = {
        'amount': 150.0,
        'hour_of_day': 14,
        'day_of_week': 3,
        'distance_from_home_km': 8.5,
        'distance_from_last_txn_km': 5.2,
        'time_since_last_txn_mins': 45.0,
        'avg_amount_last_30d': 120.0,
        'num_transactions_24h': 3,
        'merchant_risk_score': 0.15,
        'is_international': 0,
        'card_present': 1,
        'transaction_velocity': 1.2
    }
    
    prediction, probability, contributions, latency = model.predict(test_features)
    
    print(f"Prediction: {prediction}")
    print(f"Fraud Probability: {probability:.4f}")
    print(f"Latency: {latency:.2f}ms")
    print(f"Top contributions: {sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:5]}")

