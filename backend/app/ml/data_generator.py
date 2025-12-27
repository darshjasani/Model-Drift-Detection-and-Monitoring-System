"""Synthetic Data Generator for Credit Card Fraud Detection"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SyntheticDataGenerator:
    """Generate realistic credit card transaction data"""
    
    def __init__(self, seed: int = 42):
        """Initialize generator with random seed"""
        self.seed = seed
        np.random.seed(seed)
        self.feature_names = [
            'amount',
            'hour_of_day',
            'day_of_week',
            'distance_from_home_km',
            'distance_from_last_txn_km',
            'time_since_last_txn_mins',
            'avg_amount_last_30d',
            'num_transactions_24h',
            'merchant_risk_score',
            'is_international',
            'card_present',
            'transaction_velocity'
        ]
    
    def generate_baseline_data(
        self, 
        n_samples: int = 50000,
        fraud_rate: float = 0.02
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Generate baseline training data with normal distribution
        
        Args:
            n_samples: Number of samples to generate
            fraud_rate: Proportion of fraudulent transactions
            
        Returns:
            X: Feature DataFrame
            y: Labels array
        """
        logger.info(f"Generating {n_samples} baseline samples with fraud_rate={fraud_rate}")
        
        n_fraud = int(n_samples * fraud_rate)
        n_legitimate = n_samples - n_fraud
        
        # Generate legitimate transactions
        legitimate = self._generate_legitimate_transactions(n_legitimate)
        
        # Generate fraudulent transactions
        fraudulent = self._generate_fraudulent_transactions(n_fraud)
        
        # Combine and shuffle
        X = pd.concat([legitimate, fraudulent], axis=0)
        y = np.array([0] * n_legitimate + [1] * n_fraud)
        
        # Shuffle
        shuffle_idx = np.random.permutation(len(X))
        X = X.iloc[shuffle_idx].reset_index(drop=True)
        y = y[shuffle_idx]
        
        logger.info(f"Generated data: {len(X)} samples, {sum(y)} frauds ({sum(y)/len(y)*100:.2f}%)")
        
        return X, y
    
    def generate_drifted_data(
        self,
        n_samples: int = 1000,
        drift_config: Optional[dict] = None
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Generate data with intentional drift
        
        Args:
            n_samples: Number of samples
            drift_config: Configuration for drift types
            
        Returns:
            X: Feature DataFrame with drift
            y: Labels array
        """
        if drift_config is None:
            drift_config = {
                'amount_shift': 0.3,  # 30% increase in mean
                'distance_shift': 0.5,  # 50% increase
                'fraud_rate_change': 0.05  # Change fraud rate to 5%
            }
        
        fraud_rate = drift_config.get('fraud_rate_change', 0.02)
        X, y = self.generate_baseline_data(n_samples, fraud_rate)
        
        # Apply feature shifts
        if 'amount_shift' in drift_config:
            shift = drift_config['amount_shift']
            X['amount'] = X['amount'] * (1 + shift)
            logger.info(f"Applied amount shift: +{shift*100}%")
        
        if 'distance_shift' in drift_config:
            shift = drift_config['distance_shift']
            X['distance_from_home_km'] = X['distance_from_home_km'] * (1 + shift)
            logger.info(f"Applied distance shift: +{shift*100}%")
        
        if 'international_shift' in drift_config:
            # Increase proportion of international transactions
            new_rate = drift_config['international_shift']
            n_change = int(len(X) * new_rate)
            X.loc[X.sample(n_change).index, 'is_international'] = 1
            logger.info(f"Changed international transaction rate to {new_rate*100}%")
        
        return X, y
    
    def _generate_legitimate_transactions(self, n: int) -> pd.DataFrame:
        """Generate legitimate transaction features"""
        data = {
            'amount': np.random.gamma(shape=2, scale=45, size=n),  # Typical amounts
            'hour_of_day': np.random.choice(range(6, 23), size=n, p=self._get_hour_distribution()),
            'day_of_week': np.random.randint(0, 7, size=n),
            'distance_from_home_km': np.abs(np.random.normal(8, 12, size=n)),
            'distance_from_last_txn_km': np.abs(np.random.normal(5, 8, size=n)),
            'time_since_last_txn_mins': np.abs(np.random.exponential(120, size=n)),
            'avg_amount_last_30d': np.random.gamma(shape=2, scale=40, size=n),
            'num_transactions_24h': np.random.poisson(3, size=n),
            'merchant_risk_score': np.random.beta(2, 8, size=n),  # Lower risk
            'is_international': np.random.binomial(1, 0.05, size=n),
            'card_present': np.random.binomial(1, 0.85, size=n),  # Mostly card present
            'transaction_velocity': np.random.gamma(shape=1.5, scale=0.5, size=n)
        }
        
        # Clip values to realistic ranges
        data['amount'] = np.clip(data['amount'], 0.1, 5000)
        data['distance_from_home_km'] = np.clip(data['distance_from_home_km'], 0, 100)
        data['distance_from_last_txn_km'] = np.clip(data['distance_from_last_txn_km'], 0, 50)
        data['time_since_last_txn_mins'] = np.clip(data['time_since_last_txn_mins'], 1, 1440)
        data['avg_amount_last_30d'] = np.clip(data['avg_amount_last_30d'], 5, 3000)
        data['num_transactions_24h'] = np.clip(data['num_transactions_24h'], 0, 20)
        data['merchant_risk_score'] = np.clip(data['merchant_risk_score'], 0, 1)
        data['transaction_velocity'] = np.clip(data['transaction_velocity'], 0, 5)
        
        return pd.DataFrame(data)
    
    def _generate_fraudulent_transactions(self, n: int) -> pd.DataFrame:
        """Generate fraudulent transaction features (different patterns)"""
        data = {
            'amount': np.random.gamma(shape=3, scale=80, size=n),  # Higher amounts
            'hour_of_day': np.random.choice(range(0, 24), size=n),  # Any time
            'day_of_week': np.random.randint(0, 7, size=n),
            'distance_from_home_km': np.abs(np.random.normal(45, 35, size=n)),  # Far from home
            'distance_from_last_txn_km': np.abs(np.random.normal(30, 40, size=n)),  # Large jumps
            'time_since_last_txn_mins': np.abs(np.random.exponential(30, size=n)),  # Quick succession
            'avg_amount_last_30d': np.random.gamma(shape=2, scale=40, size=n),
            'num_transactions_24h': np.random.poisson(8, size=n),  # Higher frequency
            'merchant_risk_score': np.random.beta(5, 2, size=n),  # Higher risk
            'is_international': np.random.binomial(1, 0.35, size=n),  # More international
            'card_present': np.random.binomial(1, 0.25, size=n),  # Often card not present
            'transaction_velocity': np.random.gamma(shape=3, scale=1, size=n)  # Higher velocity
        }
        
        # Clip values to realistic ranges
        data['amount'] = np.clip(data['amount'], 50, 10000)
        data['distance_from_home_km'] = np.clip(data['distance_from_home_km'], 0, 500)
        data['distance_from_last_txn_km'] = np.clip(data['distance_from_last_txn_km'], 0, 500)
        data['time_since_last_txn_mins'] = np.clip(data['time_since_last_txn_mins'], 1, 1440)
        data['avg_amount_last_30d'] = np.clip(data['avg_amount_last_30d'], 5, 3000)
        data['num_transactions_24h'] = np.clip(data['num_transactions_24h'], 0, 50)
        data['merchant_risk_score'] = np.clip(data['merchant_risk_score'], 0, 1)
        data['transaction_velocity'] = np.clip(data['transaction_velocity'], 0, 10)
        
        return pd.DataFrame(data)
    
    def _get_hour_distribution(self) -> np.ndarray:
        """Get realistic hour distribution (more activity during day)"""
        # Hours 6-22 (17 hours)
        probs = np.array([0.02, 0.03, 0.04, 0.06, 0.08, 0.09, 0.09, 0.08, 0.08,
                          0.07, 0.07, 0.06, 0.06, 0.05, 0.05, 0.04, 0.03])
        return probs / probs.sum()
    
    def generate_single_transaction(
        self, 
        is_fraud: bool = False,
        drift_factor: float = 0.0
    ) -> dict:
        """
        Generate a single transaction for real-time simulation
        
        Args:
            is_fraud: Whether this should be a fraudulent transaction
            drift_factor: Amount of drift to apply (0-1)
            
        Returns:
            Dictionary of features
        """
        if is_fraud:
            data = self._generate_fraudulent_transactions(1)
        else:
            data = self._generate_legitimate_transactions(1)
        
        # Apply drift
        if drift_factor > 0:
            data['amount'] = data['amount'] * (1 + drift_factor * 0.5)
            data['distance_from_home_km'] = data['distance_from_home_km'] * (1 + drift_factor)
        
        return data.iloc[0].to_dict()


if __name__ == "__main__":
    # Test data generation
    generator = SyntheticDataGenerator()
    X, y = generator.generate_baseline_data(1000)
    print(f"Generated {len(X)} samples")
    print(f"Fraud rate: {y.sum() / len(y) * 100:.2f}%")
    print(f"\nFeature statistics:")
    print(X.describe())

