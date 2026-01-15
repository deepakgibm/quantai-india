"""
APF - Ensemble Model
XGBoost + Ridge weighted ensemble with quantile regression for confidence bands
"""

import logging
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Tuple, Optional
from sklearn.linear_model import Ridge, QuantileRegressor
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Optional XGBoost import
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available, using Ridge-only mode")


class APFEnsemble:
    """
    Adaptive Price Forecast Ensemble Model.
    
    Combines:
    - XGBoost Regressor (60% weight): Captures non-linear momentum patterns
    - Ridge Regressor (40% weight): Provides stable linear trend estimation
    - Quantile Regressors: Upper (90%) and Lower (10%) confidence bands
    """
    
    MODEL_DIR = Path(__file__).parent / "models"
    XGBOOST_WEIGHT = 0.6
    RIDGE_WEIGHT = 0.4
    
    def __init__(self, symbol: str = "default", timeframe: str = "5m"):
        self.symbol = symbol
        self.timeframe = timeframe
        self.scaler = StandardScaler()
        self.ridge_model = Ridge(alpha=1.0)
        self.xgb_model = None
        self.quantile_upper = QuantileRegressor(quantile=0.9, alpha=0.1, solver='highs')
        self.quantile_lower = QuantileRegressor(quantile=0.1, alpha=0.1, solver='highs')
        self.is_trained = False
        self.training_timestamp: Optional[str] = None
        self.feature_names = []
        
        # Ensure model directory exists
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
        if XGBOOST_AVAILABLE:
            self.xgb_model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='reg:squarederror',
                random_state=42
            )
    
    def train(self, X: np.ndarray, y: np.ndarray, feature_names: list = None) -> Dict:
        """
        Train all ensemble components.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target values
            feature_names: List of feature column names
            
        Returns:
            Dict with training metrics
        """
        if X is None or len(X) < 50:
            raise ValueError("Insufficient training data (need at least 50 samples)")
        
        self.feature_names = feature_names or []
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Ridge
        self.ridge_model.fit(X_scaled, y)
        ridge_pred = self.ridge_model.predict(X_scaled)
        ridge_mse = np.mean((ridge_pred - y) ** 2)
        
        # Train XGBoost if available
        xgb_mse = 0
        if XGBOOST_AVAILABLE and self.xgb_model is not None:
            self.xgb_model.fit(X_scaled, y)
            xgb_pred = self.xgb_model.predict(X_scaled)
            xgb_mse = np.mean((xgb_pred - y) ** 2)
        
        # Train quantile regressors for confidence bands
        try:
            self.quantile_upper.fit(X_scaled, y)
            self.quantile_lower.fit(X_scaled, y)
        except Exception as e:
            logger.warning(f"Quantile regressor training failed: {e}, using std-based bands")
        
        self.is_trained = True
        self.training_timestamp = np.datetime64('now').astype(str)
        
        metrics = {
            "ridge_mse": float(ridge_mse),
            "xgb_mse": float(xgb_mse) if XGBOOST_AVAILABLE else None,
            "n_samples": len(X),
            "n_features": X.shape[1],
            "training_timestamp": self.training_timestamp
        }
        
        logger.info(f"Ensemble trained: Ridge MSE={ridge_mse:.4f}, XGB MSE={xgb_mse:.4f}")
        return metrics
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        """
        Generate predictions with confidence bands.
        
        Args:
            X: Feature matrix for prediction
            
        Returns:
            (predicted, upper_band, lower_band, confidence_score)
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first or load a saved model.")
        
        X_scaled = self.scaler.transform(X)
        
        # Ridge prediction
        ridge_pred = self.ridge_model.predict(X_scaled)
        
        # XGBoost prediction
        if XGBOOST_AVAILABLE and self.xgb_model is not None:
            xgb_pred = self.xgb_model.predict(X_scaled)
            # Weighted ensemble
            predicted = (self.XGBOOST_WEIGHT * xgb_pred + self.RIDGE_WEIGHT * ridge_pred)
        else:
            predicted = ridge_pred
        
        # Confidence bands from quantile regression
        try:
            upper_band = self.quantile_upper.predict(X_scaled)
            lower_band = self.quantile_lower.predict(X_scaled)
        except Exception:
            # Fallback: use standard deviation
            std = np.std(predicted) if len(predicted) > 1 else predicted[0] * 0.02
            upper_band = predicted + 1.5 * std
            lower_band = predicted - 1.5 * std
        
        # Calculate confidence score (narrower bands = higher confidence)
        band_width = np.mean(upper_band - lower_band)
        price_level = np.mean(predicted)
        relative_width = band_width / price_level if price_level > 0 else 1
        confidence = max(0.0, min(1.0, 1.0 - relative_width * 10))  # Scale to 0-1
        
        return predicted, upper_band, lower_band, confidence
    
    def save(self, suffix: str = "") -> str:
        """Save model to disk."""
        filename = f"apf_{self.symbol}_{self.timeframe}{suffix}.joblib"
        path = self.MODEL_DIR / filename
        
        model_data = {
            "scaler": self.scaler,
            "ridge_model": self.ridge_model,
            "xgb_model": self.xgb_model,
            "quantile_upper": self.quantile_upper,
            "quantile_lower": self.quantile_lower,
            "is_trained": self.is_trained,
            "training_timestamp": self.training_timestamp,
            "feature_names": self.feature_names,
            "symbol": self.symbol,
            "timeframe": self.timeframe
        }
        
        joblib.dump(model_data, path)
        logger.info(f"Model saved to {path}")
        return str(path)
    
    def load(self, suffix: str = "") -> bool:
        """Load model from disk."""
        filename = f"apf_{self.symbol}_{self.timeframe}{suffix}.joblib"
        path = self.MODEL_DIR / filename
        
        if not path.exists():
            logger.warning(f"Model file not found: {path}")
            return False
        
        try:
            model_data = joblib.load(path)
            self.scaler = model_data["scaler"]
            self.ridge_model = model_data["ridge_model"]
            self.xgb_model = model_data.get("xgb_model")
            self.quantile_upper = model_data["quantile_upper"]
            self.quantile_lower = model_data["quantile_lower"]
            self.is_trained = model_data["is_trained"]
            self.training_timestamp = model_data.get("training_timestamp")
            self.feature_names = model_data.get("feature_names", [])
            logger.info(f"Model loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
