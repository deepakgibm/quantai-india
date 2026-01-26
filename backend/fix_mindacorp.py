"""
Direct MINDACORP price fix script.
Uses yfinance to get the official EOD close and updates all data sources.
"""
import psycopg2
import redis
import json
import yfinance as yf
from datetime import datetime

def fix_mindacorp_price():
    # 1. Get official EOD from yfinance
    data = yf.download(['MINDACORP.NS'], period='2d', interval='1d', auto_adjust=False, progress=False)
    
    if data.empty:
        print("ERROR: Could not fetch MINDACORP data from yfinance")
        return
    
    # Get the last available close (should be 13th Jan)
    latest_date = data.index[-1].date()
    official_close = float(data['Close'].iloc[-1].values[0])
    prev_close = float(data['Close'].iloc[-2].values[0]) if len(data) > 1 else official_close
    
    print(f"Official EOD for {latest_date}: {official_close}")
    print(f"Previous Close: {prev_close}")
    
    # 2. Update PostgreSQL - stock_candles
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    
    # Delete any existing record for this date
    cur.execute("DELETE FROM stock_candles WHERE symbol = 'MINDACORP' AND timestamp::date = %s", (latest_date,))
    
    # Insert fresh record
    cur.execute("""
        INSERT INTO stock_candles (symbol, instrument_key, timeframe, timestamp, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, ('MINDACORP', 'NSE_EQ|INE842C01021', '1d', datetime.combine(latest_date, datetime.min.time()), 
          official_close, official_close, official_close, official_close, 100000))
    
    conn.commit()
    print(f"Updated stock_candles: MINDACORP = {official_close}")
    
    # 3. Update PostgreSQL - nifty100_daily
    cur.execute("""
        INSERT INTO nifty100_daily (symbol, timestamp, open, high, low, close, volume, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, timestamp) DO UPDATE SET close = EXCLUDED.close
    """, ('MINDACORP', datetime.combine(latest_date, datetime.min.time()), 
          official_close, official_close, official_close, official_close, 100000, 'yfinance_fix'))
    
    conn.commit()
    print(f"Updated nifty100_daily: MINDACORP = {official_close}")
    conn.close()
    
    # 4. Update Redis cache
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    change_pct = ((official_close - prev_close) / prev_close * 100) if prev_close > 0 else 0
    
    snap = {
        'symbol': 'MINDACORP',
        'interval': '1day',
        'ltp': official_close,
        'prev_close': prev_close,
        'change_pct': round(change_pct, 2),
        'indicators': {'current_close': official_close, 'prev_close': prev_close},
        'signals': ['EOD_SYNC', 'YFINANCE_FIX'],
        'trend': 'BULLISH' if change_pct > 0 else 'BEARISH',
        'updated_at': datetime.now().isoformat()
    }
    
    r.set('qai:snap:MINDACORP', json.dumps(snap), ex=86400)
    print(f"Updated Redis cache: qai:snap:MINDACORP = {official_close}")
    
    # Also update qai:snap:all if it exists
    all_snaps_raw = r.get('qai:snap:all')
    if all_snaps_raw:
        all_snaps = json.loads(all_snaps_raw)
        # Find and update MINDACORP or add it
        found = False
        for i, s in enumerate(all_snaps):
            if s.get('symbol') == 'MINDACORP':
                all_snaps[i] = snap
                found = True
                break
        if not found:
            all_snaps.append(snap)
        r.set('qai:snap:all', json.dumps(all_snaps), ex=86400)
        print(f"Updated qai:snap:all with MINDACORP = {official_close}")
    
    print("\n✅ MINDACORP price fix complete!")
    print(f"   Official Close: {official_close}")
    print(f"   Change: {round(change_pct, 2)}%")

if __name__ == "__main__":
    fix_mindacorp_price()
