"""
Fix PostgreSQL sequence for stock_data table and load data.
"""

import psycopg2
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import time

# Nifty 500 symbol list (subset for quick loading)
NIFTY_50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL",
    "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE", "TITAN", "SUNPHARMA",
    "ULTRACEMCO", "HCLTECH", "WIPRO", "NTPC", "POWERGRID", "JSWSTEEL", "TATASTEEL",
    "ADANIENT", "ADANIPORTS", "ONGC", "BPCL", "COALINDIA", "GRASIM", "TECHM", "INDUSINDBK",
    "HINDALCO", "DRREDDY", "CIPLA", "DIVISLAB", "BRITANNIA", "APOLLOHOSP", "BAJAJFINSV",
    "NESTLEIND", "EICHERMOT", "HEROMOTOCO", "TATACONSUM", "SHRIRAMFIN", "BEL", "SBILIFE",
    "HDFCLIFE", "TRENT", "TATAMOTORS"
]

NIFTY_NEXT_50 = [
    "ABB", "ADANIGREEN", "AMBUJACEM", "AUROPHARMA", "BANKBARODA", "BERGEPAINT", "BOSCHLTD",
    "CANBK", "CHOLAFIN", "COLPAL", "DLF", "DABUR", "GAIL", "GODREJCP", "HAVELLS", "ICICIPRULI",
    "ICICIGI", "INDHOTEL", "INDUSTOWER", "JINDALSTEL", "LICI", "LUPIN", "MARICO", "MOTHERSON",
    "NAUKRI", "NHPC", "NMDC", "OBEROIRLTY", "PAGEIND", "PERSISTENT", "PETRONET", "PFC",
    "PIDILITIND", "PNB", "POLYCAB", "RECLTD", "SBICARD", "SHREECEM", "SIEMENS", "SRF",
    "TATAPOWER", "TORNTPHARM", "TVSMOTOR", "VEDL", "ZOMATO", "LTIM"
]

NIFTY_200_EXTRA = [
    "ACC", "ALKEM", "ASHOKLEY", "ASTRAL", "AUBANK", "BALKRISIND", "BANDHANBNK", "BATAINDIA",
    "BHEL", "BIOCON", "CANFINHOME", "COFORGE", "COROMANDEL", "CROMPTON", "DALBHARAT",
    "DEEPAKNTR", "DIXON", "ESCORTS", "EXIDEIND", "FEDERALBNK", "FORTIS", "GLENMARK", "GNFC",
    "GODREJPROP", "GRANULES", "GUJGASLTD", "HAL", "HDFCAMC", "IDFCFIRSTB", "IEX", "INDIANB",
    "INDIGO", "IRCTC", "IRFC", "IGL", "JKCEMENT", "JSWENERGY", "JUBLFOOD", "KEI", "KPITTECH",
    "LAURUSLABS", "LICHSGFIN", "LTTS", "MCX", "METROPOLIS", "MFSL", "MGL",
    "MPHASIS", "MUTHOOTFIN", "NATIONALUM", "NAVINFLUOR", "NCC", "OIL", "PIIND", "PRESTIGE",
    "PVRINOX", "RAMCOCEM", "RBLBANK", "RVNL", "SAIL", "SJVN", "SUNTV", "SYNGENE", "TATACHEM",
    "TATACOMM", "TATAELXSI", "TIINDIA", "TORNTPOWER", "UBL", "UPL", "VOLTAS", "YESBANK", "ZEEL"
]

ALL_SYMBOLS = NIFTY_50_SYMBOLS + NIFTY_NEXT_50 + NIFTY_200_EXTRA

def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='admin',
        database='quantai'
    )

def fix_sequence():
    """Fix the sequence for stock_data table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get max ID
    cursor.execute("SELECT MAX(id) FROM stock_data")
    max_id = cursor.fetchone()[0] or 0
    
    print(f"Max ID in stock_data: {max_id}")
    
    # Reset sequence
    cursor.execute(f"ALTER SEQUENCE stock_data_id_seq RESTART WITH {max_id + 1}")
    conn.commit()
    
    print(f"Sequence reset to: {max_id + 1}")
    
    cursor.close()
    conn.close()

def load_single_symbol(symbol: str, conn) -> tuple:
    """Load data for a single symbol. Returns (success, records_inserted)."""
    cursor = conn.cursor()
    yf_symbol = f"{symbol}.NS"
    records_inserted = 0
    
    try:
        # Fetch data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)
        
        ticker = yf.Ticker(yf_symbol)
        data = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        
        if data.empty:
            cursor.close()
            return (False, 0)
        
        for idx, row in data.iterrows():
            if pd.isna(row.get('Close')):
                continue
            
            timestamp = idx.to_pydatetime().replace(tzinfo=None)
            
            # Check if record already exists
            cursor.execute("""
                SELECT 1 FROM stock_data 
                WHERE symbol = %s AND timestamp = %s
                LIMIT 1
            """, (symbol, timestamp))
            
            if cursor.fetchone():
                continue
            
            # Insert new record (using 'interval' instead of 'timeframe')
            cursor.execute("""
                INSERT INTO stock_data (symbol, timestamp, open, high, low, close, volume, interval, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                symbol,
                timestamp,
                float(row.get('Open', 0) or 0),
                float(row.get('High', 0) or 0),
                float(row.get('Low', 0) or 0),
                float(row.get('Close', 0) or 0),
                int(row.get('Volume', 0) or 0),
                '1d',
                'yfinance'
            ))
            records_inserted += 1
        
        conn.commit()
        cursor.close()
        return (True, records_inserted)
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        print(f"  Error: {e}")
        return (False, 0)

def load_stock_data():
    """Load latest price data for all symbols."""
    # First fix the sequence
    print("Fixing sequence...")
    fix_sequence()
    print()
    
    conn = get_db_connection()
    
    print(f"Loading data for {len(ALL_SYMBOLS)} Nifty stocks...")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    total_records = 0
    
    for i, symbol in enumerate(ALL_SYMBOLS):
        print(f"[{i+1}/{len(ALL_SYMBOLS)}] {symbol}...", end=" ", flush=True)
        
        success, records = load_single_symbol(symbol, conn)
        
        if success:
            success_count += 1
            total_records += records
            print(f"✓ ({records} records)")
        else:
            error_count += 1
            print("✗")
        
        # Small delay to avoid rate limiting
        if (i + 1) % 20 == 0:
            print("  [Pausing to avoid rate limits...]")
            time.sleep(2)
        else:
            time.sleep(0.3)
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("DATA LOADING COMPLETE")
    print(f"✓ Successful: {success_count}")
    print(f"✗ Errors: {error_count}")
    print(f"📊 Records Inserted: {total_records}")
    print("=" * 60)

if __name__ == "__main__":
    load_stock_data()
