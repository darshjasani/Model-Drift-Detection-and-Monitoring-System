"""Drift Detection Module - PSI and KS Tests"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detect data drift using statistical methods:
    - PSI (Population Stability Index)
    - KS Test (Kolmogorov-Smirnov)
    """
    
    def __init__(
        self,
        psi_threshold: float = 0.25,
        ks_threshold: float = 0.05,
        n_bins: int = 10
    ):
        """
        Initialize drift detector
        
        Args:
            psi_threshold: PSI threshold (0.25 is industry standard)
            ks_threshold: KS test p-value threshold
            n_bins: Number of bins for PSI calculation
        """
        self.psi_threshold = psi_threshold
        self.ks_threshold = ks_threshold
        self.n_bins = n_bins
        
    def calculate_psi(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
        n_bins: int = None
    ) -> float:
        """
        Calculate Population Stability Index (PSI)
        
        PSI measures distribution shift:
        - PSI < 0.1: No significant change
        - 0.1 <= PSI < 0.25: Moderate change
        - PSI >= 0.25: Significant change (action needed)
        
        Formula: PSI = Σ (% current - % baseline) * ln(% current / % baseline)
        
        Args:
            baseline: Baseline distribution
            current: Current distribution
            n_bins: Number of bins (default: self.n_bins)
            
        Returns:
            PSI score
        """
        if n_bins is None:
            n_bins = self.n_bins
        
        # Remove NaN values
        baseline = baseline[~np.isnan(baseline)]
        current = current[~np.isnan(current)]
        
        if len(baseline) == 0 or len(current) == 0:
            logger.warning("Empty arrays provided to PSI calculation")
            return 0.0
        
        # Create bins based on baseline distribution
        try:
            min_val = min(baseline.min(), current.min())
            max_val = max(baseline.max(), current.max())
            
            # Handle case where all values are the same
            if min_val == max_val:
                return 0.0
            
            # Create bin edges
            bins = np.linspace(min_val, max_val, n_bins + 1)
            bins[0] = -np.inf  # Catch values below minimum
            bins[-1] = np.inf  # Catch values above maximum
            
            # Calculate histograms
            baseline_counts, _ = np.histogram(baseline, bins=bins)
            current_counts, _ = np.histogram(current, bins=bins)
            
            # Convert to percentages (avoid division by zero)
            baseline_percents = baseline_counts / len(baseline)
            current_percents = current_counts / len(current)
            
            # Add small epsilon to avoid log(0)
            epsilon = 1e-10
            baseline_percents = baseline_percents + epsilon
            current_percents = current_percents + epsilon
            
            # Calculate PSI
            psi = np.sum(
                (current_percents - baseline_percents) * 
                np.log(current_percents / baseline_percents)
            )
            
            return float(psi)
            
        except Exception as e:
            logger.error(f"Error calculating PSI: {e}")
            return 0.0
    
    def ks_test(
        self,
        baseline: np.ndarray,
        current: np.ndarray
    ) -> Tuple[float, float]:
        """
        Perform Kolmogorov-Smirnov test
        
        Tests if two samples come from the same distribution
        
        Args:
            baseline: Baseline distribution
            current: Current distribution
            
        Returns:
            (statistic, p_value)
        """
        # Remove NaN values
        baseline = baseline[~np.isnan(baseline)]
        current = current[~np.isnan(current)]
        
        if len(baseline) == 0 or len(current) == 0:
            return 0.0, 1.0
        
        try:
            statistic, p_value = stats.ks_2samp(baseline, current)
            return float(statistic), float(p_value)
        except Exception as e:
            logger.error(f"Error in KS test: {e}")
            return 0.0, 1.0
    
    def detect_feature_drift(
        self,
        baseline_df: pd.DataFrame,
        current_df: pd.DataFrame,
        feature_names: List[str] = None
    ) -> List[Dict]:
        """
        Detect drift for multiple features
        
        Args:
            baseline_df: Baseline feature DataFrame
            current_df: Current feature DataFrame
            feature_names: List of features to check (None = all)
            
        Returns:
            List of drift reports per feature
        """
        if feature_names is None:
            feature_names = list(baseline_df.columns)
        
        drift_reports = []
        
        for feature in feature_names:
            if feature not in baseline_df.columns or feature not in current_df.columns:
                logger.warning(f"Feature {feature} not found in data")
                continue
            
            baseline_values = baseline_df[feature].values
            current_values = current_df[feature].values
            
            # Calculate PSI
            psi_score = self.calculate_psi(baseline_values, current_values)
            
            # Perform KS test
            ks_statistic, ks_p_value = self.ks_test(baseline_values, current_values)
            
            # Determine status
            psi_drifted = psi_score >= self.psi_threshold
            ks_drifted = ks_p_value < self.ks_threshold
            
            # Determine severity
            if psi_score >= 0.5:
                severity = "high"
            elif psi_score >= 0.25:
                severity = "medium"
            elif psi_score >= 0.1:
                severity = "low"
            else:
                severity = "none"
            
            # Calculate statistics
            baseline_stats = {
                'mean': float(np.nanmean(baseline_values)),
                'std': float(np.nanstd(baseline_values)),
                'min': float(np.nanmin(baseline_values)),
                'max': float(np.nanmax(baseline_values)),
                'median': float(np.nanmedian(baseline_values))
            }
            
            current_stats = {
                'mean': float(np.nanmean(current_values)),
                'std': float(np.nanstd(current_values)),
                'min': float(np.nanmin(current_values)),
                'max': float(np.nanmax(current_values)),
                'median': float(np.nanmedian(current_values))
            }
            
            # Calculate distribution shift
            mean_change_pct = (
                (current_stats['mean'] - baseline_stats['mean']) / 
                (baseline_stats['mean'] + 1e-10) * 100
            )
            std_change_pct = (
                (current_stats['std'] - baseline_stats['std']) / 
                (baseline_stats['std'] + 1e-10) * 100
            )
            
            drift_report = {
                'feature_name': feature,
                'drift_score': psi_score,
                'drift_method': 'PSI',
                'threshold': self.psi_threshold,
                'status': 'drifted' if psi_drifted else 'stable',
                'severity': severity,
                'ks_statistic': ks_statistic,
                'ks_p_value': ks_p_value,
                'baseline_stats': baseline_stats,
                'current_stats': current_stats,
                'distribution_shift': {
                    'mean_change_pct': mean_change_pct,
                    'std_change_pct': std_change_pct
                }
            }
            
            drift_reports.append(drift_report)
        
        return drift_reports
    
    def detect_prediction_drift(
        self,
        baseline_predictions: np.ndarray,
        current_predictions: np.ndarray
    ) -> Dict:
        """
        Detect drift in prediction distribution
        
        Args:
            baseline_predictions: Baseline predictions
            current_predictions: Current predictions
            
        Returns:
            Prediction drift report
        """
        # KS test on predictions
        ks_statistic, ks_p_value = self.ks_test(baseline_predictions, current_predictions)
        
        baseline_fraud_rate = np.mean(baseline_predictions)
        current_fraud_rate = np.mean(current_predictions)
        
        change_pct = (
            (current_fraud_rate - baseline_fraud_rate) / 
            (baseline_fraud_rate + 1e-10) * 100
        )
        
        return {
            'method': 'KS_test',
            'statistic': float(ks_statistic),
            'p_value': float(ks_p_value),
            'threshold': self.ks_threshold,
            'status': 'drifted' if ks_p_value < self.ks_threshold else 'stable',
            'baseline_fraud_rate': float(baseline_fraud_rate),
            'current_fraud_rate': float(current_fraud_rate),
            'change_pct': float(change_pct)
        }
    
    def generate_recommendation(self, drift_reports: List[Dict]) -> str:
        """
        Generate actionable recommendations based on drift
        
        Args:
            drift_reports: List of feature drift reports
            
        Returns:
            Recommendation string
        """
        high_drift_features = [
            r['feature_name'] for r in drift_reports 
            if r['severity'] == 'high'
        ]
        
        medium_drift_features = [
            r['feature_name'] for r in drift_reports 
            if r['severity'] == 'medium'
        ]
        
        if high_drift_features:
            return (
                f"URGENT: Significant drift detected in {len(high_drift_features)} feature(s): "
                f"{', '.join(high_drift_features)}. Model retraining strongly recommended. "
                f"Investigate data quality and feature engineering pipeline."
            )
        elif medium_drift_features:
            return (
                f"WARNING: Moderate drift detected in {len(medium_drift_features)} feature(s): "
                f"{', '.join(medium_drift_features)}. Monitor closely and plan retraining. "
                f"Consider A/B testing new model before deployment."
            )
        else:
            return "All features stable. Continue monitoring."


if __name__ == "__main__":
    # Test drift detection
    np.random.seed(42)
    
    # Baseline data
    baseline = np.random.normal(100, 15, 10000)
    
    # No drift
    no_drift = np.random.normal(100, 15, 10000)
    
    # With drift
    with_drift = np.random.normal(130, 20, 10000)
    
    detector = DriftDetector()
    
    psi_no_drift = detector.calculate_psi(baseline, no_drift)
    psi_with_drift = detector.calculate_psi(baseline, with_drift)
    
    print(f"PSI (no drift): {psi_no_drift:.4f} - Status: {'Stable' if psi_no_drift < 0.25 else 'Drifted'}")
    print(f"PSI (with drift): {psi_with_drift:.4f} - Status: {'Stable' if psi_with_drift < 0.25 else 'Drifted'}")

