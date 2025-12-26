"""
Retry failed Nifty 500 symbols with corrected tickers
"""
import yfinance as yf
import psycopg2
from datetime import datetime
import time

# Symbol corrections - map old/wrong symbols to correct NSE tickers
SYMBOL_CORRECTIONS = {
    "TATAMOTORS": "TATAMTRDVR",  # Try DVR variant
    "ZOMATO": "ZOMATO",  # Already correct, retry
    "VEDANTA": "VEDL",  # Already have this
    "AMARAJABAT": "AMARAGBAT",  # Not on NSE anymore
    "CENTURYTEX": "CENTURY",  # Try shorter name
    "KALPATPOWR": "KALPATPOW",  # Try without R
    "LAXMIMACH": "LXCHEM",  # Merged/renamed
    "MAHINDCIE": "MAHINDCIE",  # Retry
}

# Additional Nifty 500 symbols that might be missing
ADDITIONAL_SYMBOLS = [
    "M&M",
    "ADANIPOWER",
    "ATGL", 
    "AWL",
    "JIOFIN",
    "JIOFINSER",
    "PAYTM",
    "NYKAA",
    "ZOMATO",
    "POLICYBZR",
    "DELHIVERY",
    "CARTRADE",
    "STARHEALTH",
    "RAINBOW",
    "LODHA",
    "MACROTECH",
    "TATAMTRDVR"
]

def get_db_connection():
    return psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='admin',
        database='quantai'
    )

def check_symbol_exists(cursor, symbol):
    cursor.execute("SELECT COUNT(*) FROM stock_data WHERE symbol = %s", (symbol,))
    return cursor.fetchone()[0] > 0

def load_symbol_data(symbol, start_date="2022-01-01", end_date=None):
    """Load historical data for a symbol using yfinance"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    ticker = f"{symbol}.NS"
    print(f"Fetching {ticker}...")
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, interval="1d")
        
        if df.empty:
            # Try .BO (BSE) if NSE fails
            ticker = f"{symbol}.BO"
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date, interval="1d")
        
        if df.empty:
            return None, "No data available"
        
        df = df.reset_index()
        df['symbol'] = symbol
        return df, None
    except Exception as e:
        return None, str(e)

def insert_data(cursor, df, symbol):
    """Insert data into PostgreSQL"""
    inserted = 0
    skipped = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO stock_data (symbol, timestamp, open, high, low, close, volume, interval)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, timestamp, interval) DO NOTHING
            """, (
                symbol,
                row['Date'].to_pydatetime() if hasattr(row['Date'], 'to_pydatetime') else row['Date'],
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                int(row['Volume']),
                '1d'
            ))
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"Error inserting row for {symbol}: {e}")
            skipped += 1
    
    return inserted, skipped

def main():
    print("=" * 60)
    print("Loading additional Nifty 500 symbols")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    total_inserted = 0
    total_skipped = 0
    loaded_symbols = []
    failed_symbols = []
    
    # First check existing symbols
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data WHERE interval = '1d'")
    existing_count = cursor.fetchone()[0]
    print(f"\nCurrently have {existing_count} symbols with 1d data\n")
    
    # Process additional symbols
    all_symbols = ADDITIONAL_SYMBOLS
    
    for i, symbol in enumerate(all_symbols):
        print(f"[{i+1}/{len(all_symbols)}] Processing {symbol}...")
        
        # Check if already exists
        if check_symbol_exists(cursor, symbol):
            print(f"  ⚠ Already exists, skipping")
            continue
        
        # Load data
        df, error = load_symbol_data(symbol)
        
        if df is not None and not df.empty:
            inserted, skipped = insert_data(cursor, df, symbol)
            total_inserted += inserted
            total_skipped += skipped
            loaded_symbols.append(symbol)
            conn.commit()
            print(f"  ✓ Loaded {inserted} records (skipped {skipped} duplicates)")
        else:
            failed_symbols.append({"symbol": symbol, "error": error or "No data"})
            print(f"  ✗ Failed: {error}")
        
        # Rate limiting
        time.sleep(0.5)
    
    # Final stats
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data WHERE interval = '1d'")
    final_count = cursor.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Before: {existing_count} symbols")
    print(f"After: {final_count} symbols")
    print(f"New symbols added: {len(loaded_symbols)}")
    print(f"Total records inserted: {total_inserted}")
    print(f"Failed symbols: {len(failed_symbols)}")
    
    if failed_symbols:
        print("\nFailed symbols:")
        for fs in failed_symbols:
            print(f"  - {fs['symbol']}: {fs['error']}")
    
    conn.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
