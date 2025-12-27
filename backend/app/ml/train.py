"""Model Training Script"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, classification_report
)
from xgboost import XGBClassifier
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.ml.data_generator import SyntheticDataGenerator
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """Train and evaluate XGBoost model"""
    
    def __init__(self, model_path: str = None):
        """Initialize trainer"""
        self.model_path = model_path or settings.MODEL_PATH
        Path(self.model_path).mkdir(parents=True, exist_ok=True)
        self.model = None
        self.feature_names = None
        self.training_date = None
        self.metrics = {}
        
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: pd.DataFrame = None,
        y_val: np.ndarray = None
    ):
        """
        Train XGBoost model
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
        """
        logger.info(f"Training XGBoost model on {len(X_train)} samples...")
        
        self.feature_names = list(X_train.columns)
        self.training_date = datetime.now()
        
        # Configure XGBoost for 8GB RAM (lightweight)
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=2,  # Limited parallelism for low RAM
            tree_method='hist',  # Memory efficient
            eval_metric='auc',
            scale_pos_weight=len(y_train[y_train == 0]) / len(y_train[y_train == 1])  # Handle imbalance
        )
        
        # Prepare validation set
        eval_set = []
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]
        
        # Train
        self.model.fit(
            X_train, 
            y_train,
            eval_set=eval_set if eval_set else None,
            verbose=False
        )
        
        logger.info("Training completed!")
        
        # Evaluate on training set
        train_metrics = self.evaluate(X_train, y_train, "Training")
        
        # Evaluate on validation set if provided
        if X_val is not None and y_val is not None:
            val_metrics = self.evaluate(X_val, y_val, "Validation")
            self.metrics = val_metrics
        else:
            self.metrics = train_metrics
        
        return self.metrics
    
    def evaluate(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        dataset_name: str = "Test"
    ) -> dict:
        """
        Evaluate model performance
        
        Args:
            X: Features
            y: Labels
            dataset_name: Name for logging
            
        Returns:
            Dictionary of metrics
        """
        logger.info(f"Evaluating on {dataset_name} set...")
        
        # Predictions
        y_pred = self.model.predict(X)
        y_pred_proba = self.model.predict_proba(X)[:, 1]
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y, y_pred),
            'precision': precision_score(y, y_pred, zero_division=0),
            'recall': recall_score(y, y_pred, zero_division=0),
            'f1': f1_score(y, y_pred, zero_division=0),
            'auc_roc': roc_auc_score(y, y_pred_proba)
        }
        
        # Log metrics
        logger.info(f"\n{dataset_name} Metrics:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"  Precision: {metrics['precision']:.4f}")
        logger.info(f"  Recall:    {metrics['recall']:.4f}")
        logger.info(f"  F1 Score:  {metrics['f1']:.4f}")
        logger.info(f"  AUC-ROC:   {metrics['auc_roc']:.4f}")
        
        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            logger.info(f"\nTop 5 Features:")
            for idx, row in importance.head(5).iterrows():
                logger.info(f"  {row['feature']}: {row['importance']:.4f}")
        
        return metrics
    
    def save(self, version: str = None):
        """
        Save trained model
        
        Args:
            version: Model version string
        """
        if version is None:
            version = settings.MODEL_VERSION
        
        model_file = Path(self.model_path) / f"model_{version}.joblib"
        metadata_file = Path(self.model_path) / f"metadata_{version}.joblib"
        
        # Save model
        joblib.dump(self.model, model_file)
        logger.info(f"Model saved to {model_file}")
        
        # Save metadata
        metadata = {
            'version': version,
            'training_date': self.training_date,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'model_type': 'XGBClassifier',
            'feature_count': len(self.feature_names)
        }
        joblib.dump(metadata, metadata_file)
        logger.info(f"Metadata saved to {metadata_file}")
        
        return model_file, metadata_file
    
    def load(self, version: str = None):
        """
        Load trained model
        
        Args:
            version: Model version to load
        """
        if version is None:
            version = settings.MODEL_VERSION
        
        model_file = Path(self.model_path) / f"model_{version}.joblib"
        metadata_file = Path(self.model_path) / f"metadata_{version}.joblib"
        
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_file}")
        
        self.model = joblib.load(model_file)
        metadata = joblib.load(metadata_file)
        
        self.feature_names = metadata['feature_names']
        self.training_date = metadata['training_date']
        self.metrics = metadata['metrics']
        
        logger.info(f"Model loaded: {version}")
        logger.info(f"Training date: {self.training_date}")
        logger.info(f"Validation AUC: {self.metrics.get('auc_roc', 'N/A')}")
        
        return metadata


def main():
    """Main training pipeline"""
    logger.info("=" * 60)
    logger.info("ML Drift Detection - Model Training")
    logger.info("=" * 60)
    
    # Generate synthetic data
    logger.info("\n1. Generating synthetic training data...")
    generator = SyntheticDataGenerator(seed=42)
    X, y = generator.generate_baseline_data(n_samples=50000, fraud_rate=0.02)
    
    logger.info(f"   Total samples: {len(X)}")
    logger.info(f"   Fraud samples: {sum(y)} ({sum(y)/len(y)*100:.2f}%)")
    logger.info(f"   Features: {list(X.columns)}")
    
    # Split data
    logger.info("\n2. Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )
    
    logger.info(f"   Train: {len(X_train)} samples")
    logger.info(f"   Val:   {len(X_val)} samples")
    logger.info(f"   Test:  {len(X_test)} samples")
    
    # Train model
    logger.info("\n3. Training model...")
    trainer = ModelTrainer()
    trainer.train(X_train, y_train, X_val, y_val)
    
    # Test evaluation
    logger.info("\n4. Final evaluation on test set...")
    test_metrics = trainer.evaluate(X_test, y_test, "Test")
    
    # Save model
    logger.info("\n5. Saving model...")
    model_file, metadata_file = trainer.save()
    
    logger.info("\n" + "=" * 60)
    logger.info("Training Complete!")
    logger.info("=" * 60)
    logger.info(f"Model Version: {settings.MODEL_VERSION}")
    logger.info(f"Test AUC: {test_metrics['auc_roc']:.4f}")
    logger.info(f"Model saved to: {model_file}")
    
    return trainer


if __name__ == "__main__":
    main()

