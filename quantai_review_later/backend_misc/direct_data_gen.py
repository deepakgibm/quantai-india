"""
Direct SQLite data generator - bypasses all ORM issues
"""

import sqlite3
from datetime import datetime, timedelta
import numpy as np

def generate_data():
    print("\n" + "="*60)
    print("Direct SQLite Data Generator")
    print("="*60 + "\n")
    
    # Connect directly to SQLite database
    conn = sqlite3.connect('quantai.db')
    cursor = conn.cursor()
    
    symbols = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "LT", "SBIN", "BHARTIARTL", "ITC", "BAJFINANCE",
        "KOTAKBANK", "HCLTECH", "AXISBANK", "MARUTI", "TITAN",
        "SUNPHARMA", "ULTRACEMCO", "TATAMOTORS", "ONGC", "NTPC"
    ]
    
    start_date = datetime.now() - timedelta(days=30)
    count = 0
    
    print("Inserting 6000 alpha signals (20 symbols × 30 days × 10/day)...\n")
    
    for symbol in symbols:
        np.random.seed(hash(symbol) % (2**32))
        
        for day in range(30):
            for hour in range(10):
                timestamp = start_date + timedelta(days=day, hours=hour)
                
                # Generate factor values
                rsi = 30 + np.random.rand() * 40
                macd_div = np.random.randn() * 2
                atr = 5 + np.random.rand() * 15
                boll_pos = np.random.rand()
                vwap_ratio = 0.95 + np.random.rand() * 0.1
                vol_ratio = 0.8 + np.random.rand() * 0.4
                
                # Alpha score
                alpha_score = (
                    (rsi - 50) / 50 * 0.2 +
                    macd_div * 0.3 +
                    (boll_pos - 0.5) * 0.2 +
                    (vwap_ratio - 1) * 10 * 0.3
                )
                
                # Insert
                cursor.execute("""
                    INSERT INTO alpha_signals 
                    (symbol, timestamp, rsi, macd_divergence, atr, 
                     bollinger_position, vwap_ratio, volume_ratio, 
                     alpha_score, model_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    timestamp.isoformat(),
                    rsi,
                    macd_div,
                    atr,
                    boll_pos,
                    vwap_ratio,
                    vol_ratio,
                    alpha_score,
                    "v1.0_direct",
                    datetime.now().isoformat()
                ))
                
                count += 1
        
        conn.commit()
        print(f"  ✓ {symbol}: 300 signals inserted")
    
    # Update alpha_rank for latest signals
    print("\nRanking signals by alpha_score...")
    
    cursor.execute("""
        SELECT id, alpha_score 
        FROM alpha_signals 
        ORDER BY timestamp DESC, alpha_score DESC 
        LIMIT 100
    """)
    
    ranked = cursor.fetchall()
    for rank, (signal_id, score) in enumerate(ranked[:20], 1):
        cursor.execute("UPDATE alpha_signals SET alpha_rank = ? WHERE id = ?", (rank, signal_id))
    
    conn.commit()
    
    print(f"\n" + "="*60)
    print(f"✅ SUCCESS! {count} signals inserted")
    print("="*60)
    
    # Show top 5 signals
    cursor.execute("""
        SELECT symbol, alpha_score, alpha_rank 
        FROM alpha_signals 
        WHERE alpha_rank IS NOT NULL 
        ORDER BY alpha_rank 
        LIMIT 5
    """)
    
    print("\nTop 5 Signals:")
    for symbol, score, rank in cursor.fetchall():
        print(f"  #{rank}: {symbol:12s} - Score: {score:.4f}")
    
    print("\n" + "="*60)
    print("Ready to test!")
    print("="*60)
    print("\n1. Login: demo@example.com / testpass123")
    print("2. Go to AlphaPrime page")
    print("3. Click 'Refresh' to see signals")
    print("4. Click 'Train Model' (needs 1000+ records)")
    print("\n")
    
    conn.close()

if __name__ == "__main__":
    generate_data()
