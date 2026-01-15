"""
APF - Offline Trainer
CLI script for training APF models offline.

Usage:
    python -m backend.ml.trainer --symbol RELIANCE --timeframe 5m
    python -m backend.ml.trainer --symbol ALL --timeframe 5m  # Train for all symbols
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.feature_builder import FeatureBuilder
from ml.ensemble import APFEnsemble
from services.db_data_fetcher import get_db_data_fetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_training_symbols() -> list:
    """Get list of symbols to train."""
    # Top Nifty 50 symbols
    return [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC",
        "BAJFINANCE", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
        "HCLTECH", "SUNPHARMA", "TITAN", "WIPRO", "ULTRACEMCO"
    ]


def train_model(symbol: str, timeframe: str) -> bool:
    """
    Train APF model for a single symbol.
    
    Args:
        symbol: Stock symbol
        timeframe: Candle timeframe
        
    Returns:
        True if training successful
    """
    logger.info(f"Training APF model for {symbol} {timeframe}")
    
    # Fetch historical data
    fetcher = get_db_data_fetcher()
    end_date = datetime.now()
    
    # Adjust lookback based on timeframe
    if timeframe == "1d":
        start_date = end_date - timedelta(days=365)
    elif timeframe == "1h":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=60)
    
    df = fetcher.get_historical_data(
        symbol, 
        timeframe, 
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )
    
    if df is None or len(df) < 100:
        logger.warning(f"Insufficient data for {symbol} (got {len(df) if df is not None else 0} rows)")
        return False
    
    logger.info(f"Loaded {len(df)} candles for {symbol}")
    
    # Build features
    feature_builder = FeatureBuilder()
    X, y, timestamps = feature_builder.get_feature_matrix(df)
    
    if X is None or len(X) < 50:
        logger.warning(f"Feature building failed for {symbol}")
        return False
    
    logger.info(f"Built {len(X)} feature samples with {X.shape[1]} features")
    
    # Train model
    model = APFEnsemble(symbol=symbol, timeframe=timeframe)
    metrics = model.train(X, y, feature_builder.feature_names)
    
    logger.info(f"Training metrics: {metrics}")
    
    # Save model
    path = model.save()
    logger.info(f"Model saved to {path}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Train APF models offline")
    parser.add_argument("--symbol", type=str, default="ALL", help="Symbol to train (or ALL)")
    parser.add_argument("--timeframe", type=str, default="5m", help="Timeframe (5m, 15m, 1h, 1d)")
    
    args = parser.parse_args()
    
    logger.info(f"APF Trainer started: symbol={args.symbol}, timeframe={args.timeframe}")
    
    if args.symbol.upper() == "ALL":
        symbols = get_training_symbols()
    else:
        symbols = [args.symbol.upper()]
    
    success_count = 0
    fail_count = 0
    
    for symbol in symbols:
        try:
            if train_model(symbol, args.timeframe):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"Failed to train {symbol}: {e}")
            fail_count += 1
    
    logger.info(f"Training complete: {success_count} success, {fail_count} failed")


if __name__ == "__main__":
    main()
