"""
APF - Predictor
Inference engine for Adaptive Price Forecast
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from .feature_builder import FeatureBuilder
from .schemas import ForecastResponse

logger = logging.getLogger(__name__)


class APFPredictor:
    """
    Adaptive Price Forecast Predictor.
    
    Orchestrates data fetching, feature building, and prediction.
    Uses WebSocket → REST → Database fallback for data sourcing.
    """
    
    # Minimum candles required for prediction
    MIN_HISTORY = 50
    
    def __init__(self):
        self.feature_builder = FeatureBuilder()
        self._model_cache: Dict[str, Any] = {}
        self._data_fetcher = None
        
    def _get_data_fetcher(self):
        """Lazy load data fetcher."""
        if self._data_fetcher is None:
            from services.db_data_fetcher import get_db_data_fetcher
            self._data_fetcher = get_db_data_fetcher()
        return self._data_fetcher
    
    def _get_model(self, symbol: str, timeframe: str) -> APFEnsemble:
        """Get or load model for symbol/timeframe combination."""
        from .ensemble import APFEnsemble
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key not in self._model_cache:
            model = APFEnsemble(symbol=symbol, timeframe=timeframe)
            # Try to load pre-trained model
            if not model.load():
                logger.info(f"No pre-trained model for {cache_key}, will train on-demand")
            self._model_cache[cache_key] = model
        
        return self._model_cache[cache_key]
    
    async def predict(
        self,
        symbol: str,
        timeframe: str = "5m",
        horizon: int = 10
    ) -> ForecastResponse:
        """
        Generate price forecast for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., RELIANCE)
            timeframe: Candle timeframe (5m, 15m, 1h, 1d)
            horizon: Number of future candles to predict
            
        Returns:
            ForecastResponse with actual, predicted, and confidence bands
        """
        logger.info(f"APF Predict: {symbol} {timeframe} horizon={horizon}")
        
        # Step 1: Fetch historical data
        df, data_source = await self._fetch_data(symbol, timeframe)
        
        if df is None or len(df) < self.MIN_HISTORY:
            raise ValueError(f"Insufficient data for {symbol} (need {self.MIN_HISTORY}+ candles)")
        
        # Step 2: Build features
        features_df = self.feature_builder.build_features(df)
        if features_df is None:
            raise ValueError(f"Feature building failed for {symbol}")
        
        # Drop NaN rows from feature building
        features_df = features_df.dropna()
        
        if len(features_df) < 30:
            raise ValueError(f"Insufficient valid data after feature building")
        
        # Step 3: Get or train model
        model = self._get_model(symbol, timeframe)
        
        if not model.is_trained:
            # Train on available data (excluding last few for validation)
            train_size = len(features_df) - horizon
            train_df = features_df.iloc[:train_size]
            
            X_train, y_train, _ = self.feature_builder.get_feature_matrix(
                df.iloc[:train_size + 30]  # Need buffer for feature building
            )
            
            if X_train is not None and len(X_train) > 50:
                model.train(X_train, y_train, self.feature_builder.feature_names)
                model.save()
            else:
                raise ValueError("Insufficient data for model training")
        
        # Step 4: Prepare output arrays
        timestamps = []
        actual = []
        predicted = []
        upper_band = []
        lower_band = []
        
        # Historical actual prices
        for idx, row in features_df.iterrows():
            timestamps.append(idx.isoformat() if hasattr(idx, 'isoformat') else str(idx))
            actual.append(float(row['close']))
            predicted.append(None)  # No prediction for historical
            upper_band.append(None)
            lower_band.append(None)
        
        # Step 5: Generate predictions for future candles
        last_features = features_df[self.feature_builder.feature_names].iloc[-1:].values
        last_timestamp = features_df.index[-1]
        last_close = features_df['close'].iloc[-1]
        
        # Generate future timestamps based on timeframe
        tf_minutes = self._timeframe_to_minutes(timeframe)
        
        # Iterative prediction for horizon
        current_features = last_features.copy()
        predictions_raw = []
        
        for i in range(horizon):
            # Predict next value
            pred, upper, lower, conf = model.predict(current_features)
            pred_value = float(pred[0])
            predictions_raw.append({
                'pred': pred_value,
                'upper': float(upper[0]),
                'lower': float(lower[0])
            })
            
            # Generate future timestamp
            future_ts = last_timestamp + timedelta(minutes=tf_minutes * (i + 1))
            timestamps.append(future_ts.isoformat())
            actual.append(None)  # No actual for future
            predicted.append(round(pred_value, 2))
            upper_band.append(round(float(upper[0]), 2))
            lower_band.append(round(float(lower[0]), 2))
            
            # Update features for next iteration (simplified auto-regression)
            # In production, this would be more sophisticated
            current_features = self._update_features_for_prediction(
                current_features, pred_value, last_close
            )
            last_close = pred_value
        
        # Calculate overall confidence
        _, _, _, confidence = model.predict(last_features)
        
        return ForecastResponse(
            symbol=symbol,
            timeframe=timeframe,
            timestamps=timestamps,
            actual=actual,
            predicted=predicted,
            upper_band=upper_band,
            lower_band=lower_band,
            confidence=round(confidence, 3),
            model_version="apf_v1",
            data_source=data_source,
            last_trained=model.training_timestamp
        )
    
    async def _fetch_data(self, symbol: str, timeframe: str) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Fetch historical data with WebSocket → REST → DB fallback.
        
        Returns:
            (DataFrame, data_source) where data_source is "LIVE", "REST", or "DB"
        """
        # Get date range (last 30 days for short-term models)
        end_date = datetime.now()
        
        # Adjust lookback based on timeframe
        if timeframe == "1d":
            start_date = end_date - timedelta(days=365)
        elif timeframe == "1h":
            start_date = end_date - timedelta(days=60)
        else:
            start_date = end_date - timedelta(days=30)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Try database (primary for historical data)
        fetcher = self._get_data_fetcher()
        df = fetcher.get_historical_data(symbol, timeframe, start_str, end_str)
        
        if df is not None and len(df) > 0:
            return df, "DB"
        
        logger.warning(f"No data available for {symbol} {timeframe}")
        return None, "UNAVAILABLE"
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes."""
        mapping = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440
        }
        return mapping.get(timeframe, 5)
    
    def _update_features_for_prediction(
        self, 
        features: np.ndarray, 
        new_pred: float,
        prev_close: float
    ) -> np.ndarray:
        """
        Update feature vector for next prediction step.
        Simplified auto-regressive update.
        """
        updated = features.copy()
        
        # This is a simplified update - in production would be more sophisticated
        # Update return-based features
        if prev_close > 0:
            new_return = (new_pred - prev_close) / prev_close
            # Assuming first feature is 'returns'
            if updated.shape[1] > 0:
                updated[0, 0] = new_return
        
        return updated


# Singleton instance
_apf_predictor = None


def get_apf_predictor() -> APFPredictor:
    """Get singleton APF Predictor instance."""
    global _apf_predictor
    if _apf_predictor is None:
        _apf_predictor = APFPredictor()
    return _apf_predictor
