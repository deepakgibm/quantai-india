"""
Forecast Algorithm Registry
Extensible registry of forecast algorithms with standardized interface.
"""

import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from .schemas import (
    AlgorithmInfo,
    ForecastCandle,
    ForecastMetrics,
    ForecastRunResponse,
    AlgorithmMetadata
)

logger = logging.getLogger(__name__)


class ForecastAlgorithm(ABC):
    """
    Abstract base class for all forecast algorithms.
    
    Each algorithm must implement:
    - metadata: Algorithm info for API discovery
    - predict: Generate forecast from historical data
    """
    
    @property
    @abstractmethod
    def metadata(self) -> AlgorithmInfo:
        """Return algorithm metadata."""
        pass
    
    @abstractmethod
    def predict(
        self,
        df: pd.DataFrame,
        horizon: int,
        confidence_level: float = 0.95
    ) -> Tuple[List[float], List[float], List[float], float]:
        """
        Generate price forecast from historical OHLCV data.
        
        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume]
            horizon: Number of future candles to predict
            confidence_level: Confidence level for bands (0.68 or 0.95)
            
        Returns:
            Tuple of (predicted_prices, upper_band, lower_band, confidence_score)
        """
        pass
    
    def calculate_volatility_label(self, df: pd.DataFrame) -> str:
        """Calculate volatility label from historical data."""
        if len(df) < 20:
            return "Medium"
        
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized
        
        if volatility < 0.2:
            return "Low"
        elif volatility < 0.4:
            return "Medium"
        else:
            return "High"


# ============================================================================
# Algorithm Implementations
# ============================================================================

class AdaptiveEnsembleV2(ForecastAlgorithm):
    """
    Adaptive Ensemble v2 - Default recommended algorithm.
    Combines XGBoost + Ridge regression with quantile-based confidence bands.
    Uses the existing APFEnsemble implementation.
    """
    
    @property
    def metadata(self) -> AlgorithmInfo:
        return AlgorithmInfo(
            id="adaptive_ensemble_v2",
            name="Adaptive Ensemble",
            version="2.3",
            type="ensemble",
            recommended=True,
            supports_confidence_bands=True,
            supported_timeframes=["1m", "5m", "15m", "30m", "1h", "1d"],
            max_horizon=50,
            description="XGBoost + Ridge weighted ensemble with quantile regression for confidence bands. Best for intraday and swing trading.",
            features_used=["OHLCV", "RSI", "MACD", "EMA", "Volatility", "Volume Profile"],
            estimated_latency_ms=300
        )
    
    def predict(
        self,
        df: pd.DataFrame,
        horizon: int,
        confidence_level: float = 0.95
    ) -> Tuple[List[float], List[float], List[float], float]:
        """Use existing APF ensemble predictor logic."""
        from .feature_builder import FeatureBuilder
        from .ensemble import APFEnsemble
        
        # Build features
        feature_builder = FeatureBuilder()
        features_df = feature_builder.build_features(df)
        
        if features_df is None or len(features_df) < 50:
            raise ValueError("Insufficient data for Adaptive Ensemble (need 50+ candles)")
        
        # Drop NaN rows from feature building
        features_df = features_df.dropna()
        
        if len(features_df) < 30:
            raise ValueError("Insufficient data after feature processing")
        
        # Get feature column names (exclude target and OHLCV)
        feature_cols = [col for col in features_df.columns if col not in 
                       ['open', 'high', 'low', 'close', 'volume', 'target', 'timestamp']]
        
        # Prepare training data - use features to predict next close
        X = features_df[feature_cols].iloc[:-1].values
        y = features_df['close'].iloc[1:].values
        
        # Ensure X and y have same length
        min_len = min(len(X), len(y))
        X = X[:min_len]
        y = y[:min_len]
        
        # Train ensemble
        ensemble = APFEnsemble(symbol="forecast", timeframe="runtime")
        ensemble.train(X, y, feature_names=feature_cols)
        
        # Generate predictions
        predicted = []
        upper_band = []
        lower_band = []
        
        last_features = features_df[feature_cols].iloc[-1:].values
        last_close = df['close'].iloc[-1]
        
        for _ in range(horizon):
            pred, upper, lower, conf = ensemble.predict(last_features)
            predicted.append(float(pred[0]))
            upper_band.append(float(upper[0]))
            lower_band.append(float(lower[0]))
            
            # Update features for next prediction (simplified autoregressive)
            if len(last_features[0]) > 0:
                last_features = self._update_features(last_features, pred[0], last_close)
                last_close = pred[0]
        
        # Adjust bands based on confidence level
        if confidence_level != 0.90:  # Default quantile is 90%
            z_factor = 1.96 if confidence_level >= 0.95 else 1.0  # 95% -> 1.96, 68% -> 1.0
            band_width = [(u - l) / 2 for u, l in zip(upper_band, lower_band)]
            upper_band = [p + w * z_factor / 1.5 for p, w in zip(predicted, band_width)]
            lower_band = [p - w * z_factor / 1.5 for p, w in zip(predicted, band_width)]
        
        confidence = conf if 'conf' in dir() else 0.75
        return predicted, upper_band, lower_band, confidence
    
    def _update_features(self, features: np.ndarray, new_pred: float, prev_close: float) -> np.ndarray:
        """Simple feature update for autoregressive prediction."""
        updated = features.copy()
        # Update return-based features (assume first feature is return)
        if updated.shape[1] > 0:
            updated[0, 0] = (new_pred - prev_close) / prev_close if prev_close > 0 else 0
        return updated


class XGBoostFast(ForecastAlgorithm):
    """
    XGBoost Fast - Lightweight XGBoost-only model for quick predictions.
    Lower latency than ensemble but may have slightly lower accuracy.
    """
    
    @property
    def metadata(self) -> AlgorithmInfo:
        return AlgorithmInfo(
            id="xgboost_fast",
            name="XGBoost Fast",
            version="1.0",
            type="ml",
            recommended=False,
            supports_confidence_bands=True,
            supported_timeframes=["1m", "5m", "15m", "30m", "1h"],
            max_horizon=30,
            description="Lightweight XGBoost model optimized for speed. Best for scalping and high-frequency signals.",
            features_used=["OHLCV", "RSI", "EMA", "ATR"],
            estimated_latency_ms=150
        )
    
    def predict(
        self,
        df: pd.DataFrame,
        horizon: int,
        confidence_level: float = 0.95
    ) -> Tuple[List[float], List[float], List[float], float]:
        """XGBoost-only prediction with volatility-based bands."""
        # Calculate simple features
        df = df.copy()
        df['returns'] = df['close'].pct_change()
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        df['atr'] = self._calculate_atr(df, 14)
        
        df = df.dropna()
        if len(df) < 30:
            raise ValueError("Insufficient data for XGBoost Fast (need 30+ candles)")
        
        # Prepare features
        feature_cols = ['returns', 'ema_9', 'ema_21', 'rsi', 'atr']
        X = df[feature_cols].values[:-1]
        y = df['close'].iloc[1:].values
        
        # Train XGBoost
        try:
            import xgboost as xgb
            model = xgb.XGBRegressor(
                n_estimators=50,
                max_depth=4,
                learning_rate=0.1,
                random_state=42
            )
            model.fit(X, y)
        except ImportError:
            # Fallback to simple moving average
            return self._fallback_prediction(df, horizon, confidence_level)
        
        # Generate predictions
        predicted = []
        last_close = df['close'].iloc[-1]
        last_features = df[feature_cols].iloc[-1:].values
        atr = df['atr'].iloc[-1]
        
        for _ in range(horizon):
            pred = model.predict(last_features)[0]
            predicted.append(float(pred))
            
            # Update features
            new_return = (pred - last_close) / last_close if last_close > 0 else 0
            last_features[0, 0] = new_return
            last_close = pred
        
        # Calculate confidence bands based on ATR
        z_factor = 1.96 if confidence_level >= 0.95 else 1.0
        upper_band = [p + atr * z_factor for p in predicted]
        lower_band = [p - atr * z_factor for p in predicted]
        
        confidence = 0.70
        return predicted, upper_band, lower_band, confidence
    
    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df['high']
        low = df['low']
        close = df['close']
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    def _fallback_prediction(
        self,
        df: pd.DataFrame,
        horizon: int,
        confidence_level: float
    ) -> Tuple[List[float], List[float], List[float], float]:
        """Fallback to EMA-based prediction when XGBoost unavailable."""
        ema = df['close'].ewm(span=9, adjust=False).mean().iloc[-1]
        std = df['close'].rolling(20).std().iloc[-1]
        
        predicted = [ema] * horizon
        z_factor = 1.96 if confidence_level >= 0.95 else 1.0
        upper_band = [ema + std * z_factor] * horizon
        lower_band = [ema - std * z_factor] * horizon
        
        return predicted, upper_band, lower_band, 0.5


class ARIMAStable(ForecastAlgorithm):
    """
    ARIMA Stable - Statistical time series model.
    More interpretable, good for longer-term trends.
    
    Note: This is a placeholder implementation using exponential smoothing.
    TODO: Replace with proper ARIMA when statsmodels is available.
    """
    
    @property
    def metadata(self) -> AlgorithmInfo:
        return AlgorithmInfo(
            id="arima_stable",
            name="ARIMA Stable",
            version="1.0",
            type="statistical",
            recommended=False,
            supports_confidence_bands=True,
            supported_timeframes=["15m", "30m", "1h", "1d"],
            max_horizon=50,
            description="Statistical ARIMA-based model for trend analysis. Best for positional trading and longer timeframes.",
            features_used=["Close Price", "Trend", "Seasonality"],
            estimated_latency_ms=200
        )
    
    def predict(
        self,
        df: pd.DataFrame,
        horizon: int,
        confidence_level: float = 0.95
    ) -> Tuple[List[float], List[float], List[float], float]:
        """
        ARIMA-style prediction using exponential smoothing.
        TODO: Implement proper ARIMA with statsmodels.
        """
        if len(df) < 30:
            raise ValueError("Insufficient data for ARIMA Stable (need 30+ candles)")
        
        close = df['close'].values
        
        # Double exponential smoothing (Holt's method)
        alpha = 0.3  # Level smoothing
        beta = 0.1   # Trend smoothing
        
        # Initialize
        level = close[0]
        trend = close[1] - close[0] if len(close) > 1 else 0
        
        # Fit on historical data
        for price in close[1:]:
            prev_level = level
            level = alpha * price + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend
        
        # Forecast
        predicted = []
        for h in range(1, horizon + 1):
            forecast = level + h * trend
            predicted.append(float(forecast))
        
        # Calculate prediction intervals
        residuals = []
        temp_level = close[0]
        temp_trend = close[1] - close[0] if len(close) > 1 else 0
        
        for price in close[1:]:
            prev_level = temp_level
            temp_level = alpha * price + (1 - alpha) * (temp_level + temp_trend)
            temp_trend = beta * (temp_level - prev_level) + (1 - beta) * temp_trend
            residuals.append(price - (temp_level + temp_trend))
        
        std_residual = np.std(residuals) if residuals else close.std() * 0.02
        
        # Confidence bands grow with horizon
        z_factor = 1.96 if confidence_level >= 0.95 else 1.0
        upper_band = [p + z_factor * std_residual * np.sqrt(h) for h, p in enumerate(predicted, 1)]
        lower_band = [p - z_factor * std_residual * np.sqrt(h) for h, p in enumerate(predicted, 1)]
        
        confidence = 0.65
        return predicted, upper_band, lower_band, confidence


class TransformerInformerDL(ForecastAlgorithm):
    """
    Transformer/Informer Deep Learning - Advanced attention-based model for price forecasting.
    Uses symbol and timeframe embeddings for global generalization.
    """
    
    def __init__(self):
        self.pipeline = None
        self.trainer = None
        self.mapper = None

    def _lazy_init(self, num_features: int = 12):
        """Lazy initialization to avoid model overhead on startup."""
        if self.trainer is None:
            from .trainer import QuantAITrainer
            from .metadata_utils import SymbolMapper
            from services.feature_pipeline import get_feature_pipeline
            
            self.pipeline = get_feature_pipeline()
            self.mapper = SymbolMapper()
            
            # These counts should ideally be from a config or registry
            num_symbols = 1000 # High upper bound for embeddings
            num_timeframes = 8
            
            self.trainer = QuantAITrainer(
                num_features=num_features,
                num_symbols=num_symbols,
                num_timeframes=num_timeframes
            )
            self.trainer.load_model()

    @property
    def metadata(self) -> AlgorithmInfo:
        return AlgorithmInfo(
            id="transformer_informer_dl",
            name="Transformer Informer DL",
            version="1.0",
            type="dl",
            recommended=True,
            supports_confidence_bands=True,
            supported_timeframes=["5m", "15m", "1h", "1d"],
            max_horizon=30,
            description="Encoder-only Transformer with Multi-Head Attention. Uses Symbol & Timeframe embeddings for superior generalization.",
            features_used=["Log-Returns", "Momentum", "Volatility", "Symbol Embeddings"],
            estimated_latency_ms=450
        )
    
    def predict(
        self,
        df: pd.DataFrame,
        horizon: int,
        confidence_level: float = 0.95
    ) -> Tuple[List[float], List[float], List[float], float]:
        """
        Forecasting using the Transformer model.
        """
        if len(df) < 50:
            raise ValueError("Insufficient data for Transformer DL (need 50+ candles)")
        
        # 1. Initialize logic
        self._lazy_init()
        
        # 2. Build features
        features_df = self.pipeline.build_features(df)
        if features_df.empty:
            raise ValueError("Feature extraction failed")
            
        # 3. Prepare inputs
        feature_cols = [
            'log_return', 'volatility_20', 'rsi_14', 
            'macd_line', 'macd_signal', 'macd_hist',
            'bb_pct_b', 'atr_14_pct', 'adx_14', 
            'plus_di', 'minus_di', 'volume_ratio_20'
        ]
        
        # Get sequence (last seq_len steps)
        seq_len = 50
        seq_data = features_df[feature_cols].tail(seq_len).values.astype(np.float32)
        
        if len(seq_data) < seq_len:
            # Pad if needed, but we usually should have enough data
            padding = np.zeros((seq_len - len(seq_data), len(feature_cols)), dtype=np.float32)
            seq_data = np.vstack([padding, seq_data])
            
        x_tensor = torch.from_numpy(seq_data)
        
        # Resolve embeddings
        # We need symbol from df or context. If not provided, use a default index.
        symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else "DEFAULT"
        timeframe = df['timeframe'].iloc[0] if 'timeframe' in df.columns else "1d"
        
        from .metadata_utils import TIMEFRAME_TO_IDX
        s_idx = self.mapper.get_idx(symbol)
        t_idx = TIMEFRAME_TO_IDX.get(timeframe, 6)
        
        # 4. Model Inference
        import torch
        with torch.no_grad():
            self.trainer.model.eval()
            # s_idx, t_idx as tensors
            s_tensor = torch.tensor([s_idx]).to(self.trainer.device)
            t_tensor = torch.tensor([t_idx]).to(self.trainer.device)
            x_tensor = x_tensor.unsqueeze(0).to(self.trainer.device)
            
            returns, vol, quantiles = self.trainer.model(x_tensor, s_tensor, t_tensor)
            
            # predicted_returns: [batch, 3] -> t+1, t+3, t+5
            ret_np = returns.cpu().numpy()[0]
            # quantiles: [batch, 5] -> 5%, 25%, 50%, 75%, 95%
            q_np = quantiles.cpu().numpy()[0] 
            
        # 5. Project back to price
        last_close = df['close'].iloc[-1]
        
        # For simplicity, we interpolate between t+1, t+3, t+5 for the horizon
        predicted_prices = []
        for i in range(1, horizon + 1):
            if i == 1:
                r = ret_np[0]
            elif i <= 3:
                # linear interpolation between 1 and 3
                weight = (i - 1) / 2
                r = ret_np[0] * (1 - weight) + ret_np[1] * weight
            else:
                # linear interpolation between 3 and 5 or just extension
                weight = min(1.0, (i - 3) / 2)
                r = ret_np[1] * (1 - weight) + ret_np[2] * weight
            
            predicted_prices.append(float(last_close * np.exp(r)))
            
        # 6. Bands using quantiles (for t+1) and scaled for horizon
        # 95% band uses q[0] (5%) and q[4] (95%)
        # 68% band uses q[1] (25%) and q[3] (75%)
        
        if confidence_level >= 0.95:
            low_q, high_q = q_np[0], q_np[4]
        else:
            low_q, high_q = q_np[1], q_np[3]
            
        upper_band = []
        lower_band = []
        
        for i, p in enumerate(predicted_prices, 1):
            # Scale uncertainty with sqrt of time
            scale = np.sqrt(i)
            upper_band.append(float(last_close * np.exp(high_q * scale)))
            lower_band.append(float(last_close * np.exp(low_q * scale)))
            
        confidence = 0.85
        return predicted_prices, upper_band, lower_band, confidence


# ============================================================================
# Algorithm Registry
# ============================================================================

class AlgorithmRegistry:
    """
    Central registry for all forecast algorithms.
    Singleton pattern for consistent access across the application.
    """
    
    _instance = None
    _algorithms: Dict[str, ForecastAlgorithm] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_algorithms()
        return cls._instance
    
    def _initialize_algorithms(self):
        """Register default algorithms."""
        self._algorithms = {}
        self.register(AdaptiveEnsembleV2())
        self.register(XGBoostFast())
        self.register(TransformerInformerDL())
        self.register(ARIMAStable())
        logger.info(f"Algorithm Registry initialized with {len(self._algorithms)} algorithms")
    
    def register(self, algorithm: ForecastAlgorithm):
        """Register an algorithm."""
        self._algorithms[algorithm.metadata.id] = algorithm
        logger.debug(f"Registered algorithm: {algorithm.metadata.id}")
    
    def get(self, algorithm_id: str) -> Optional[ForecastAlgorithm]:
        """Get an algorithm by ID."""
        return self._algorithms.get(algorithm_id)
    
    def get_default(self) -> ForecastAlgorithm:
        """Get the recommended/default algorithm."""
        for algo in self._algorithms.values():
            if algo.metadata.recommended:
                return algo
        # Fallback to first algorithm
        return list(self._algorithms.values())[0] if self._algorithms else None
    
    def list_all(self) -> List[AlgorithmInfo]:
        """Get metadata for all registered algorithms."""
        return [algo.metadata for algo in self._algorithms.values()]
    
    def run_forecast(
        self,
        algorithm_id: str,
        df: pd.DataFrame,
        symbol: str,
        exchange: str,
        timeframe: str,
        horizon: int,
        confidence_level: float = 0.95,
        include_confidence_bands: bool = True
    ) -> ForecastRunResponse:
        """
        Run a forecast with the specified algorithm.
        
        Args:
            algorithm_id: ID of algorithm to use
            df: Historical OHLCV DataFrame
            symbol: Stock symbol
            exchange: Stock exchange
            timeframe: Candle timeframe
            horizon: Prediction horizon
            confidence_level: Confidence level for bands
            include_confidence_bands: Whether to include bands in response
            
        Returns:
            ForecastRunResponse with predictions and metadata
        """
        start_time = time.time()
        request_id = f"FR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        warnings = []
        
        # Get algorithm
        algorithm = self.get(algorithm_id)
        if not algorithm:
            algorithm = self.get_default()
            warnings.append(f"Algorithm '{algorithm_id}' not found, using default")
        
        # Validate timeframe
        if timeframe not in algorithm.metadata.supported_timeframes:
            warnings.append(f"Timeframe '{timeframe}' not optimal for this algorithm")
        
        # Validate horizon
        if horizon > algorithm.metadata.max_horizon:
            horizon = algorithm.metadata.max_horizon
            warnings.append(f"Horizon capped to {horizon} for this algorithm")
        
        # Run prediction
        try:
            predicted, upper_band, lower_band, confidence = algorithm.predict(
                df, horizon, confidence_level
            )
        except Exception as e:
            logger.error(f"Forecast failed for {symbol}: {e}")
            raise RuntimeError(f"Forecast failed: {str(e)}")
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Calculate metrics
        last_price = df['close'].iloc[-1]
        first_pred = predicted[0] if predicted else last_price
        predicted_move_pct = ((predicted[-1] - last_price) / last_price * 100) if predicted else 0
        volatility_label = algorithm.calculate_volatility_label(df)
        
        # Build forecast candles
        last_timestamp = pd.to_datetime(df.index[-1] if hasattr(df.index, 'name') else df['timestamp'].iloc[-1])
        forecast_candles = []
        
        # Determine timeframe delta
        tf_minutes = self._timeframe_to_minutes(timeframe)
        
        for i, (pred, upper, lower) in enumerate(zip(predicted, upper_band, lower_band)):
            ts = last_timestamp + timedelta(minutes=tf_minutes * (i + 1))
            forecast_candles.append(ForecastCandle(
                timestamp=ts.isoformat(),
                close=round(pred, 2),
                upper=round(upper, 2) if include_confidence_bands else None,
                lower=round(lower, 2) if include_confidence_bands else None,
                is_forecast=True
            ))
        
        # Build input candles summary (last 10)
        candles_input = []
        for idx in range(max(0, len(df) - 10), len(df)):
            row = df.iloc[idx]
            ts = df.index[idx] if hasattr(df.index, 'name') else row.get('timestamp', idx)
            candles_input.append({
                "timestamp": str(ts),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row.get('volume', 0))
            })
        
        # Build confidence bands dict
        confidence_bands = None
        if include_confidence_bands:
            confidence_bands = {
                "upper": [round(u, 2) for u in upper_band],
                "lower": [round(l, 2) for l in lower_band]
            }
        
        return ForecastRunResponse(
            request_id=request_id,
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            horizon=horizon,
            algorithm=AlgorithmMetadata(
                id=algorithm.metadata.id,
                name=algorithm.metadata.name,
                version=algorithm.metadata.version
            ),
            generated_at=datetime.now().isoformat(),
            candles_input=candles_input,
            forecast=forecast_candles,
            confidence_bands=confidence_bands,
            metrics=ForecastMetrics(
                confidence_score=round(confidence, 3),
                predicted_move_pct=round(predicted_move_pct, 2),
                volatility_label=volatility_label,
                model_latency_ms=latency_ms
            ),
            warnings=warnings,
            error=None
        )
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes."""
        tf_map = {
            "1m": 1, "3m": 3, "5m": 5, "15m": 15,
            "30m": 30, "1h": 60, "4h": 240, "1d": 1440
        }
        return tf_map.get(timeframe, 5)


# Module-level singleton access
def get_algorithm_registry() -> AlgorithmRegistry:
    """Get the singleton algorithm registry instance."""
    return AlgorithmRegistry()
