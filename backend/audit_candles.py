"""
Audit script to analyze stock_candles table data coverage.
"""
import psycopg2

def audit_stock_candles():
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    
    print("=" * 80)
    print("STOCK_CANDLES DATA AUDIT")
    print("=" * 80)
    
    # 1. Overall counts by timeframe
    print("\n📊 DATA BY TIMEFRAME:")
    print("-" * 60)
    cur.execute("""
        SELECT 
            timeframe,
            COUNT(*) as total_rows,
            COUNT(DISTINCT symbol) as symbols,
            MIN(timestamp)::date as oldest,
            MAX(timestamp)::date as newest
        FROM stock_candles
        GROUP BY timeframe
        ORDER BY timeframe
    """)
    rows = cur.fetchall()
    print(f"{'Timeframe':<12} {'Rows':>10} {'Symbols':>10} {'Oldest':>15} {'Newest':>15}")
    print("-" * 60)
    for r in rows:
        print(f"{r[0]:<12} {r[1]:>10} {r[2]:>10} {str(r[3]):>15} {str(r[4]):>15}")
    
    # 2. Gap analysis for 1d timeframe (most critical)
    print("\n📅 1D TIMEFRAME - LAST 10 TRADING DAYS:")
    print("-" * 60)
    cur.execute("""
        SELECT 
            timestamp::date as trade_date,
            COUNT(DISTINCT symbol) as symbols
        FROM stock_candles
        WHERE timeframe = '1d'
        GROUP BY timestamp::date
        ORDER BY trade_date DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    print(f"{'Date':>15} {'Symbols':>10}")
    print("-" * 30)
    for r in rows:
        print(f"{str(r[0]):>15} {r[1]:>10}")
    
    # 3. Sample symbols with data
    print("\n📈 SAMPLE SYMBOLS (first 10):")
    print("-" * 60)
    cur.execute("""
        SELECT 
            symbol,
            COUNT(*) as total_candles,
            COUNT(DISTINCT timeframe) as timeframes
        FROM stock_candles
        GROUP BY symbol
        ORDER BY symbol
        LIMIT 10
    """)
    rows = cur.fetchall()
    print(f"{'Symbol':<15} {'Candles':>10} {'Timeframes':>12}")
    print("-" * 40)
    for r in rows:
        print(f"{r[0]:<15} {r[1]:>10} {r[2]:>12}")
    
    # 4. Check stock_master coverage
    print("\n🏢 STOCK_MASTER vs STOCK_CANDLES:")
    print("-" * 60)
    cur.execute("SELECT COUNT(*) FROM stock_master")
    master_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM stock_candles")
    candles_symbols = cur.fetchone()[0]
    print(f"Stock Master Symbols: {master_count}")
    print(f"Stock Candles Symbols: {candles_symbols}")
    print(f"Coverage: {candles_symbols/master_count*100:.1f}%")
    
    # 5. Missing symbols
    cur.execute("""
        SELECT sm.symbol 
        FROM stock_master sm
        LEFT JOIN (SELECT DISTINCT symbol FROM stock_candles) sc ON sm.symbol = sc.symbol
        WHERE sc.symbol IS NULL
        LIMIT 20
    """)
    missing = cur.fetchall()
    if missing:
        print(f"\n⚠️ MISSING SYMBOLS ({len(missing)} shown):")
        print(", ".join([m[0] for m in missing]))
    else:
        print("\n✅ All symbols have candle data!")
    
    conn.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    audit_stock_candles()
