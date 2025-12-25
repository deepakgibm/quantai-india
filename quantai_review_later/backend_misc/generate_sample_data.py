"""
Quick sample data generator for AlphaPrime testing

Generates synthetic OHLCV data and calculates factors for immediate testing.
This bypasses the slow Upstox API historical load (which takes hours).
"""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from database import AsyncSessionLocal
from models import *  # Import all base models first
from models_alpha import StockData, AlphaSignal
from features.alpha_prime.factors import FactorEngine


async def generate_sample_data(days=30, symbols_count=20):
    """
    Generate sample OHLCV data for testing
    
    Args:
        days: Number of days of data
        symbols_count: Number of symbols to generate
    """
    print(f"Generating {days} days of sample data for {symbols_count} symbols...")
    
    symbols = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "LT", "SBIN", "BHARTIARTL", "ITC", "BAJFINANCE",
        "KOTAKBANK", "HCLTECH", "AXISBANK", "MARUTI", "TITAN",
        "SUNPHARMA", "ULTRACEMCO", "TATAMOTORS", "ONGC", "NTPC"
    ][:symbols_count]
    
    all_data = []
    start_date = datetime.now() - timedelta(days=days)
    
    for symbol in symbols:
        # Generate base price with random walk
        np.random.seed(hash(symbol) % (2**32))
        base_price = 100 + np.random.rand() * 900
        
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            
            # Generate 50 data points per day (simulating intraday)
            for minute in range(0, 50):
                timestamp = current_date + timedelta(minutes=minute * 5)
                
                # Random walk for price
                price_change = np.random.randn() * 2
                base_price += price_change
                
                # OHLCV
                open_price = base_price + np.random.randn()
                high_price = max(open_price, base_price + abs(np.random.randn()))
                low_price = min(open_price, base_price - abs(np.random.randn()))
                close_price = base_price
                volume = int(np.random.randint(1000, 10000))
                
                all_data.append({
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })
    
    df = pd.DataFrame(all_data)
    print(f"Generated {len(df)} records")
    
    return df


async def insert_stock_data(df):
    """Insert stock data into database"""
    print("Inserting stock data into database...")
    
    async with AsyncSessionLocal() as session:
        inserted = 0
        for _, row in df.iterrows():
            stock_data = StockData(
                symbol=row['symbol'],
                timestamp=row['timestamp'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume'],
                interval="5min",
                source="synthetic"
            )
            session.add(stock_data)
            inserted += 1
            
            if inserted % 100 == 0:
                await session.commit()
                print(f"  Inserted {inserted} records...")
        
        await session.commit()
        print(f"✓ Inserted total {inserted} stock data records")


async def calculate_and_store_factors():
    """Calculate factors from stock data and store as signals"""
    print("\nCalculating alpha factors...")
    
    async with AsyncSessionLocal() as session:
        # Fetch all stock data
        from sqlalchemy import select
        result = await session.execute(select(StockData))
        stock_data = result.scalars().all()
        
        if not stock_data:
            print("No stock data found!")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'symbol': sd.symbol,
            'timestamp': sd.timestamp,
            'open': sd.open,
            'high': sd.high,
            'low': sd.low,
            'close': sd.close,
            'volume': sd.volume
        } for sd in stock_data])
        
        print(f"Loaded {len(df)} stock data records")
        
        # Calculate factors
        df_with_factors = FactorEngine.calculate_all_factors(df)
        
        # Drop rows with NaN (from rolling calculations)
        df_with_factors = df_with_factors.dropna()
        
        print(f"Calculated factors for {len(df_with_factors)} records")
        
        # Insert alpha signals
        inserted = 0
        for _, row in df_with_factors.iterrows():
            # Simple alpha score: weighted combination of normalized factors
            alpha_score = (
                (row['rsi'] - 50) / 50 * 0.2 +  # RSI contribution
                row.get('macd_divergence', 0) * 0.3 +  # MACD contribution
                (row.get('bollinger_position', 0.5) - 0.5) * 0.2 +  # Bollinger contribution
                (row.get('vwap_ratio', 1) - 1) * 0.3  # VWAP contribution
            )
            
            signal = AlphaSignal(
                symbol=row['symbol'],
                timestamp=row['timestamp'],
                rsi=row.get('rsi'),
                macd=row.get('macd'),
                macd_signal=row.get('macd_signal'),
                macd_divergence=row.get('macd_divergence'),
                atr=row.get('atr'),
                bollinger_upper=row.get('bollinger_upper'),
                bollinger_lower=row.get('bollinger_lower'),
                bollinger_position=row.get('bollinger_position'),
                vwap=row.get('vwap'),
                volume_sma=row.get('volume_sma'),
                vwap_ratio=row.get('vwap_ratio'),
                volume_ratio=row.get('volume_ratio'),
                alpha_score=alpha_score,
                model_version="v1.0_synthetic"
            )
            session.add(signal)
            inserted += 1
            
            if inserted % 100 == 0:
                await session.commit()
                print(f"  Inserted {inserted} signals...")
        
        await session.commit()
        print(f"✓ Inserted total {inserted} alpha signals")


async def main():
    print("\n" + "="*60)
    print("AlphaPrime Sample Data Generator")
    print("="*60 + "\n")
    
    # Generate sample data
    df = await generate_sample_data(days=30, symbols_count=20)
    
    # Insert into database
    await insert_stock_data(df)
    
    # Calculate and store factors
    await calculate_and_store_factors()
    
    print("\n" + "="*60)
    print("✅ Sample data generation complete!")
    print("="*60)
    print("\nYou can now:")
    print("1. Train the model: python features/alpha_prime/model.py")
    print("2. Or use the dashboard: Click 'Train Model' button")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
