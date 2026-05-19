# app/services/statistical_significance.py
import numpy as np
from scipy import stats
from typing import Dict, Tuple


class StatisticalSignificance:
    """Track statistical significance of betting performance"""
    
    @staticmethod
    def calculate_confidence_interval(clv_values: list, confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for CLV"""
        n = len(clv_values)
        if n < 30:
            # Use t-distribution for small samples
            t_value = stats.t.ppf((1 + confidence) / 2, n - 1)
            std_error = np.std(clv_values) / np.sqrt(n)
            margin = t_value * std_error
        else:
            # Use normal distribution for large samples
            z_value = stats.norm.ppf((1 + confidence) / 2)
            std_error = np.std(clv_values) / np.sqrt(n)
            margin = z_value * std_error
        
        mean = np.mean(clv_values)
        return mean - margin, mean + margin
    
    @staticmethod
    def is_statistically_significant(clv_values: list, threshold: float = 0.02) -> Dict:
        """Check if CLV is statistically significant"""
        n = len(clv_values)
        if n < 30:
            return {
                "is_significant": False,
                "reason": f"Insufficient samples (n={n}, need >=30)",
                "required_samples": 30 - n
            }
        
        # One-sample t-test
        t_stat, p_value = stats.ttest_1samp(clv_values, 0)
        
        # Check if mean > threshold
        mean_clv = np.mean(clv_values)
        
        return {
            "is_significant": p_value < 0.05 and mean_clv > threshold,
            "mean_clv": mean_clv,
            "p_value": p_value,
            "sample_size": n,
            "confidence_interval": StatisticalSignificance.calculate_confidence_interval(clv_values),
            "interpretation": "Significant edge" if (p_value < 0.05 and mean_clv > threshold) else
                            "Insufficient evidence" if p_value >= 0.05 else
                            "Edge detected but below threshold"
        }
    
    @staticmethod
    def required_sample_size(current_mean: float, current_std: float, target_mean: float = 0.02) -> int:
        """Calculate required sample size for statistical significance"""
        if current_mean <= 0:
            return float('inf')
        
        effect_size = abs(current_mean - target_mean) / current_std
        # Simplified calculation - would use power analysis in production
        return int(np.ceil((1.96 * current_std / effect_size) ** 2))