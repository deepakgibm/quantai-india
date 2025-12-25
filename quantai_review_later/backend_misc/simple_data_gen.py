"""
Ultra-simple data generator using raw SQL
"""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta
import numpy as np
from sqlalchemy import text

from database import AsyncSessionLocal


async def generate_simple_data():
    print("\n" + "="*60)
    print("Simple SQL Data Generator")
    print("="*60 + "\n")
    
    async with AsyncSessionLocal() as session:
        # Generate 6000 simple signal records (20 symbols × 30 days × 10/day)
        symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
                   "LT", "SBIN", "BHARTIARTL", "ITC", "BAJFINANCE",
                   "KOTAKBANK", "HCLTECH", "AXISBANK", "MARUTI", "TITAN",
                   "SUNPHARMA", "ULTRACEMCO", "TATAMOTORS", "ONGC", "NTPC"]
        
        start_date = datetime.now() - timedelta(days=30)
        count = 0
        
        print("Inserting alpha signals...")
        
        for symbol in symbols:
            np.random.seed(hash(symbol) % (2**32))
            
            for day in range(30):
                for hour in range(10):
                    timestamp = start_date + timedelta(days=day, hours=hour)
                    
                    rsi = 30 + np.random.rand() * 40
                    alpha_score = np.random.randn() * 0.3
                    
                    # Raw SQL insert
                    await session.execute(
                        text("""
                        INSERT INTO alpha_signals 
                        (symbol, timestamp, rsi, macd_divergence, atr, 
                         bollinger_position, vwap_ratio, volume_ratio, 
                         alpha_score, model_version, created_at)
                        VALUES 
                        (:symbol, :timestamp, :rsi, :macd, :atr,
                         :boll, :vwap, :vol,
                         :alpha, :version, :created)
                        """),
                        {
                            "symbol": symbol,
                            "timestamp": timestamp,
                            "rsi": rsi,
                            "macd": np.random.randn(),
                            "atr": 5 + np.random.rand() * 10,
                            "boll": np.random.rand(),
                            "vwap": 0.95 + np.random.rand() * 0.1,
                            "vol": 0.8 + np.random.rand() * 0.4,
                            "alpha": alpha_score,
                            "version": "v1.0_simple",
                            "created": datetime.now()
                        }
                    )
                    count += 1
            
            # Commit after each symbol
            await session.commit()
            print(f"  ✓ {symbol}: 300 signals")
        
        print(f"\n✅ Total: {count} alpha signals inserted")
        print("\nLogin credentials:")
        print("  Email: demo@example.com")
        print("  Password: testpass123")
        print("\nYou can now train the model!")
        print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(generate_simple_data())
