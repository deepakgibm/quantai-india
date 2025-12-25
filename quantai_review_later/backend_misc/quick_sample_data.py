"""
Simplified sample data generator for AlphaPrime - Direct insertion without FKs
"""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta
import numpy as np

from database import AsyncSessionLocal
from models import *  # Import base models first
from models_alpha import AlphaSignal


async def generate_sample_signals(days=30, symbols_count=20):
    """
    Generate sample alpha signals directly (bypass stock_data FK)
    """
    print("\n" + "="*60)
    print("AlphaPrime Quick Sample Data Generator")
    print("="*60 + "\n")
    
    symbols = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "LT", "SBIN", "BHARTIARTL", "ITC", "BAJFINANCE",
        "KOTAKBANK", "HCLTECH", "AXISBANK", "MARUTI", "TITAN",
        "SUNPHARMA", "ULTRACEMCO", "TATAMOTORS", "ONGC", "NTPC"
    ][:symbols_count]
    
    print(f"Generating {days} days of signals for {symbols_count} symbols...")
    
    start_date = datetime.now() - timedelta(days=days)
    total_records = 0
    
    async with AsyncSessionLocal() as session:
        for symbol in symbols:
            np.random.seed(hash(symbol) % (2**32))
            
            for day in range(days):
                current_date = start_date + timedelta(days=day)
                
                # Generate 10 data points per day (simulating market hours)
                for hour in range(10):
                    timestamp = current_date + timedelta(hours=hour)
                    
                    # Generate realistic factor values
                    rsi = 30 + np.random.rand() * 40  # 30-70 range
                    macd_div = np.random.randn() * 2
                    atr = 5 + np.random.rand() * 15
                    bollinger_pos = np.random.rand()  # 0-1
                    vwap_ratio = 0.95 + np.random.rand() * 0.1  # 0.95-1.05
                    volume_ratio = 0.8 + np.random.rand() * 0.4  # 0.8-1.2
                    
                    # Simple alpha score calculation
                    alpha_score = (
                        (rsi - 50) / 50 * 0.2 +
                        macd_div * 0.3 +
                        (bollinger_pos - 0.5) * 0.2 +
                        (vwap_ratio - 1) *10 * 0.3
                    )
                    
                    signal = AlphaSignal(
                        symbol=symbol,
                        timestamp=timestamp,
                        rsi=rsi,
                        macd=rsi / 10,  # Simplified
                        macd_signal=rsi / 10 - 0.5,
                        macd_divergence=macd_div,
                        atr=atr,
                        bollinger_upper=100 + atr,
                        bollinger_lower=100 - atr,
                        bollinger_position=bollinger_pos,
                        vwap=100,
                        volume_sma=50000,
                        vwap_ratio=vwap_ratio,
                        volume_ratio=volume_ratio,
                        alpha_score=alpha_score,
                        model_version="v1.0_quickstart"
                    )
                    
                    session.add(signal)
                    total_records += 1
                
                # Commit after each day
                if day % 5 == 0:
                    await session.commit()
                    print(f"  {symbol}: Day {day+1}/{days} - {total_records} signals...")
        
        # Final commit
        await session.commit()
        
        print(f"\n✅ Generated {total_records} alpha signals")
        print(f"   ({symbols_count} symbols × {days} days × 10 readings)")
        
        # Rank signals by alpha_score for latest timestamp
        from sqlalchemy import select, desc
        latest_signals = await session.execute(
            select(AlphaSignal)
            .order_by(desc(AlphaSignal.timestamp))
            .limit(100)
        )
        
        signals_list = list(latest_signals.scalars().all())
        signals_list.sort(key=lambda x: x.alpha_score or 0, reverse=True)
        
        for rank, sig in enumerate(signals_list[:20], 1):
            sig.alpha_rank = rank
        
        await session.commit()
        
        print(f"\n" + "="*60)
        print("✅ Sample Data Generation Complete!")
        print("="*60)
        print("\nTop 5 Signals (by alpha_score):")
        for sig in signals_list[:5]:
            print(f"  #{sig.alpha_rank}: {sig.symbol:12s} - Score: {sig.alpha_score:.4f}")
        
        print("\nNext Steps:")
        print("1. Login: demo@example.com / testpass123")
        print("2. Navigate to AlphaPrime dashboard")
        print("3. Click 'Train Model' button")
        print()


if __name__ == "__main__":
    asyncio.run(generate_sample_signals(days=30, symbols_count=20))
