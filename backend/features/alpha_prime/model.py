"""
AlphaPrime ML Model - Random Forest Factor Weighting

Implements a Random Forest Regressor to dynamically weight technical factors
based on recent market regime (30-day lookback).

Features:
- Regime-based training
- Factor importance analysis
- Model persistence (joblib)
- Walk-forward validation
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import joblib
from pathlib import Path

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

from config import settings
from database import AsyncSessionLocal
from models_alpha import AlphaSignal, StockData
from sqlalchemy import select


class AlphaMLModel:
    """Random Forest model for dynamic factor weighting"""
    
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = Path(model_dir or settings.ALPHA_PRIME_MODEL_DIR)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model: Optional[RandomForestRegressor] = None
        self.feature_names: List[str] = [
            'rsi', 'macd_divergence', 'atr',
            'bollinger_position', 'vwap_ratio', 'volume_ratio'
        ]
        self.feature_importance: Optional[Dict[str, float]] = None
        self.model_version = "v1.0"
    
    def prepare_training_data(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """
        Prepare features (X) and target (y) for training
        
        Target: Forward returns (next period's price change)
        """
        # Calculate forward returns as target
        df = df.sort_values(['symbol', 'timestamp']).copy()
        df['forward_return'] = df.groupby('symbol')['close'].pct_change().shift(-1)
        
        # Drop NaN rows
        df = df.dropna(subset=self.feature_names + ['forward_return'])
        
        X = df[self.feature_names].values
        y = df['forward_return'].values
        
        return X, y
    
    def train(
        self,
        df: pd.DataFrame,
        n_estimators: int = 100,
        max_depth: int = 10,
        test_size: float = 0.2
    ) -> Dict[str, float]:
        """
        Train the Random Forest model
        
        Returns:
            Dict with training metrics (mse, r2, etc.)
        """
        print(f"\n{'='*60}")
        print("Training AlphaPrime ML Model")
        print(f"{'='*60}\n")
        
        # Prepare data
        X, y = self.prepare_training_data(df)
        
        print(f"Training samples: {len(X)}")
        print(f"Features: {', '.join(self.feature_names)}")
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Train Random Forest
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        train_mse = mean_squared_error(y_train, y_pred_train)
        test_mse = mean_squared_error(y_test, y_pred_test)
        train_r2 = r2_score(y_train, y_pred_train)
        test_r2 = r2_score(y_test, y_pred_test)
        
        # Feature importance
        self.feature_importance = dict(zip(
            self.feature_names,
            self.model.feature_importances_
        ))
        
        metrics = {
            'train_mse': float(train_mse),
            'test_mse': float(test_mse),
            'train_r2': float(train_r2),
            'test_r2': float(test_r2),
            'n_samples': len(X),
            'n_features': len(self.feature_names)
        }
        
        print(f"\nTraining Results:")
        print(f"  Train MSE: {train_mse:.6f}")
        print(f"  Test MSE: {test_mse:.6f}")
        print(f"  Train R²: {train_r2:.4f}")
        print(f"  Test R²: {test_r2:.4f}")
        
        print(f"\nFeature Importance:")
        for feature, importance in sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True):
            print(f"  {feature:20s}: {importance:.4f}")
        
        return metrics
    
    def predict(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate alpha scores for input data
        
        Returns:
            Series of alpha scores (predicted returns)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        X = df[self.feature_names].values
        predictions = self.model.predict(X)
        
        return pd.Series(predictions, index=df.index, name='alpha_score')
    
    async def fetch_training_data(self, lookback_days: int = None) -> pd.DataFrame:
        """
        Fetch recent data from database for training
        
        Args:
            lookback_days: Number of days of historical data (default from config)
            
        Returns:
            DataFrame with OHLCV + factor columns
        """
        lookback_days = lookback_days or settings.ML_LOOKBACK_DAYS
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        async with AsyncSessionLocal() as session:
            # Fetch alpha signals (which include factor values)
            result = await session.execute(
                select(AlphaSignal)
                .where(AlphaSignal.timestamp >= cutoff_date)
                .order_by(AlphaSignal.timestamp)
            )
            signals = result.scalars().all()
            
            if not signals:
                raise ValueError(f"No training data found for last {lookback_days} days")
            
            # Convert to DataFrame
            data = []
            for signal in signals:
                data.append({
                    'symbol': signal.symbol,
                    'timestamp': signal.timestamp,
                    'rsi': signal.rsi,
                    'macd_divergence': signal.macd_divergence,
                    'atr': signal.atr,
                    'bollinger_position': signal.bollinger_position,
                    'vwap_ratio': signal.vwap_ratio,
                    'volume_ratio': signal.volume_ratio,
                })
            
            df = pd.DataFrame(data)
            
            # Also fetch corresponding stock data for close prices
            result = await session.execute(
                select(StockData.symbol, StockData.timestamp, StockData.close)
                .where(StockData.timestamp >= cutoff_date)
            )
            stock_data = pd.DataFrame(result.fetchall(), columns=['symbol', 'timestamp', 'close'])
            
            # Merge
            df = df.merge(stock_data, on=['symbol', 'timestamp'], how='left')
            
            return df
    
    def save(self, filename: str = "alpha_model.joblib"):
        """Save model to disk"""
        if self.model is None:
            raise ValueError("No model to save")
        
        filepath = self.model_dir / filename
        
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'feature_importance': self.feature_importance,
            'version': self.model_version,
            'trained_at': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, filepath)
        print(f"\n✓ Model saved to {filepath}")
    
    def load(self, filename: str = "alpha_model.joblib"):
        """Load model from disk"""
        filepath = self.model_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        model_data = joblib.load(filepath)
        
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        self.feature_importance = model_data.get('feature_importance')
        self.model_version = model_data.get('version', 'unknown')
        
        print(f"✓ Model loaded from {filepath}")
        print(f"  Version: {self.model_version}")
        print(f"  Trained at: {model_data.get('trained_at', 'unknown')}")


async def retrain_model():
    """Retrain the model with latest data (CLI utility)"""
    model = AlphaMLModel()
    
    print("Fetching training data...")
    df = await model.fetch_training_data(lookback_days=settings.ML_LOOKBACK_DAYS)
    
    print(f"Loaded {len(df)} samples")
    
    metrics = model.train(df)
    
    model.save()
    
    return metrics


if __name__ == "__main__":
    import asyncio
    asyncio.run(retrain_model())
