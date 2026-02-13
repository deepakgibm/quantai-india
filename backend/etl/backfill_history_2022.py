
import os
import sys
import time
import asyncio
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
backend_dir = project_root / 'backend'
sys.path.append(str(backend_dir))
sys.path.append(str(project_root))

try:
    from services.instrument_resolver import resolve_instrument_id, get_instrument_info
    from services.upstox_client import get_upstox_client
    from config import settings
except ImportError:
    from backend.services.instrument_resolver import resolve_instrument_id, get_instrument_info
    from backend.services.upstox_client import get_upstox_client
    from backend.config import settings

# Explicit NIFTY 500 List (Complete List or subset provided previously)
NIFTY_500_SYMBOLS = [
    "360ONE", "3MINDIA", "AADHARHFC", "AARTIIND", "AAVAS", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ABLBL",
    "ABREL", "ABSLAMC", "ACC", "ACE", "ACMESOLAR", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER",
    "AEGISLOG", "AEGISVOPAK", "AFCONS", "AFFLE", "AGARWALEYE", "AIAENG", "AIIL", "AJANTPHARM", "AKUMS", "AKZOINDIA",
    "ALKEM", "ALKYLAMINE", "ALOKINDS", "AMBER", "AMBUJACEM", "ANANDRATHI", "ANANTRAJ", "ANGELONE", "APARINDS", "APLAPOLLO",
    "APLLTD", "APOLLOHOSP", "APOLLOTYRE", "APTUS", "ARE&M", "ASAHIINDIA", "ASHOKLEY", "ASIANPAINT", "ASTERDM", "ASTRAL",
    "ASTRAZEN", "ATGL", "ATHERENERG", "ATUL", "AUBANK", "AUROPHARMA", "AWL", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV",
    "BAJAJHFL", "BAJAJHLDNG", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "BASF", "BATAINDIA",
    "BAYERCROP", "BBTC", "BDL", "BEL", "BEML", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHARTIHEXA", "BHEL",
    "BIKAJI", "BIOCON", "BLS", "BLUEDART", "BLUEJET", "BLUESTARCO", "BOSCHLTD", "BPCL", "BRIGADE", "BRITANNIA",
    "BSE", "BSOFT", "CAMPUS", "CAMS", "CANBK", "CANFINHOME", "CAPLIPOINT", "CARBORUNIV", "CASTROLIND", "CCL",
    "CDSL", "CEATLTD", "CENTRALBK", "CENTURYPLY", "CERA", "CESC", "CGCL", "CGPOWER", "CHALET", "CHAMBLFERT",
    "CHENNPETRO", "CHOICEIN", "CHOLAFIN", "CHOLAHLDNG", "CIPLA", "CLEAN", "COALINDIA", "COCHINSHIP", "COFORGE", "COHANCE",
    "COLPAL", "CONCOR", "CONCORDBIO", "COROMANDEL", "CRAFTSMAN", "CREDITACC", "CRISIL", "CROMPTON", "CUB", "CUMMINSIND",
    "CYIENT", "DABUR", "DALBHARAT", "DATAPATTNS", "DCMSHRIRAM", "DEEPAKFERT", "DEEPAKNTR", "DELHIVERY", "DEVYANI", "DIVISLAB",
    "DIXON", "DLF", "DMART", "DOMS", "DRREDDY", "EICHERMOT", "EIDPARRY", "EIHOTEL", "ELECON", "ELGIEQUIP",
    "EMAMILTD", "EMCURE", "ENDURANCE", "ENGINERSIN", "ERIS", "ESCORTS", "ETERNAL", "EXIDEIND", "FACT", "FEDERALBNK",
    "FINCABLES", "FINPIPE", "FIRSTCRY", "FIVESTAR", "FLUOROCHEM", "FORCEMOT", "FORTIS", "FSL", "GAIL", "GESHIP",
    "GICRE", "GILLETTE", "GLAND", "GLAXO", "GLENMARK", "GMDCLTD", "GMRAIRPORT", "GODFRYPHLP", "GODIGIT", "GODREJAGRO",
    "GODREJCP", "GODREJIND", "GODREJPROP", "GPIL", "GRANULES", "GRAPHITE", "GRASIM", "GRAVITA", "GRSE", "GSPL",
    "GUJGASLTD", "GVT&D", "HAL", "HAPPSTMNDS", "HAVELLS", "HBLENGINE", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE",
    "HEG", "HEROMOTOCO", "HEXT", "HFCL", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "HINDZINC", "HOMEFIRST",
    "HONASA", "HONAUT", "HSCL", "HUDCO", "HYUNDAI", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDFCFIRSTB", "IEX",
    "IFCI", "IGIL", "IGL", "IIFL", "IKS", "INDGN", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIANB",
    "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "INOXINDIA", "INOXWIND", "INTELLECT", "IOB", "IOC", "IPCALAB",
    "IRB", "IRCON", "IRCTC", "IREDA", "IRFC", "ITC", "ITCHOTELS", "ITI", "J&KBANK", "JBCHEPHARM",
    "JBMA", "JINDALSAW", "JINDALSTEL", "JIOFIN", "JKCEMENT", "JKTYRE", "JMFINANCIL", "JPPOWER", "JSL", "JSWENERGY",
    "JSWINFRA", "JSWSTEEL", "JUBLFOOD", "JUBLINGREA", "JUBLPHARMA", "JWL", "JYOTHYLAB", "JYOTICNC", "KAJARIACER", "KALYANKJIL",
    "KARURVYSYA", "KAYNES", "KEC", "KEI", "KFINTECH", "KIMS", "KIRLOSBROS", "KIRLOSENG", "KOTAKBANK", "KPIL",
    "KPITTECH", "KPRMILL", "KSB", "LALPATHLAB", "LATENTVIEW", "LAURUSLABS", "LEMONTREE", "LICHSGFIN", "LICI", "LINDEINDIA",
    "LLOYDSME", "LODHA", "LT", "LTF", "LTFOODS", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN",
    "MAHABANK", "MAHSCOOTER", "MAHSEAMLES", "MANKIND", "MAPMYINDIA", "MARICO", "MARUTI", "MAXHEALTH", "MAZDOCK", "MCX",
    "MEDANTA", "METROPOLIS", "MFSL", "MGL", "MINDACORP", "MMTC", "MOTHERSON", "MOTILALOFS", "MPHASIS", "MRF",
    "MRPL", "MSUMI", "MUTHOOTFIN", "NATCOPHARM", "NATIONALUM", "NAUKRI", "NAVA", "NAVINFLUOR", "NBCC", "NCC",
    "NESTLEIND", "NH", "NHPC", "NLCINDIA", "NMDC", "NSLNISP", "NTPC", "NTPCGREEN", "NUVAMA", "NUVOCO",
    "NYKAA", "OBEROIRLTY", "OIL", "OLECTRA", "ONGC", "PAGEIND", "PERSISTENT", "PETRONET", "PFC", "PGHH",
    "PHOENIXLTD", "PIDILITIND", "PIIND", "PNB", "PNBHOUSING", "POLYCAB", "POLYMED", "POONAWALLA", "POWERGRID", "POWERINDIA",
    "PRAJIND", "PRESTIGE", "PVRINOX", "RADICO", "RAMCOCEM", "RBLBANK", "RECLTD", "REDINGTON", "RELIANCE", "RVNL",
    "SAIL", "SBFC", "SBICARD", "SBILIFE", "SBIN", "SCHAEFFLER", "SCHNEIDER", "SHREECEM", "SHRIRAMFIN", "SIEMENS",
    "SJVN", "SKFINDIA", "SOBHA", "SOLARINDS", "SONACOMS", "SRF", "STARHEALTH", "SUNDARMFIN", "SUNDRMFAST", "SUNPHARMA",
    "SUNTV", "SUPREMEIND", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAELXSI", "TATAINVEST", "TATAPOWER", "TATASTEEL",
    "TCS", "TECHM", "TECHNOE", "THELEELA", "THERMAX", "TIINDIA", "TIMKEN", "TITAN", "TORNTPHARM", "TORNTPOWER",
    "TRENT", "TRIDENT", "TRITURBINE", "TVSMOTOR", "UBL", "UCOBANK", "ULTRACEMCO", "UNIONBANK", "UPL", "USHAMART",
    "UTIAMC", "VBL", "VEDL", "VGUARD", "VIJAYA", "VOLTAS", "WELCORP", "WELSPUNLIV", "WHIRLPOOL", "WIPRO",
    "WOCKPHARMA", "YESBANK", "ZEEL", "ZENSARTECH", "ZENTEC", "ZYDUSLIFE"
]

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'admin',
    'database': 'quantai'
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_job_status():
    """Initialize etl_job_status with pending symbols"""
    conn = get_connection()
    cursor = conn.cursor()
    job_name = 'backfill_2022'
    
    print("Initializing ETL Job Status...")
    for symbol in NIFTY_500_SYMBOLS:
        cursor.execute("""
            INSERT INTO etl_job_status (job_name, symbol, status)
            VALUES (%s, %s, 'PENDING')
            ON CONFLICT (job_name, symbol) DO NOTHING
        """, (job_name, symbol))
    conn.commit()
    conn.close()

def get_next_symbol():
    """Get next PENDING or FAILED symbol"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol FROM etl_job_status 
        WHERE job_name = 'backfill_2022' AND status IN ('PENDING', 'FAILED')
        ORDER BY id ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """)
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def update_status(symbol, status, error=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE etl_job_status 
        SET status = %s, last_updated = CURRENT_TIMESTAMP, error_msg = %s
        WHERE job_name = 'backfill_2022' AND symbol = %s
    """, (status, error, symbol))
    conn.commit()
    conn.close()

def insert_candles_history(conn, instrument_id, df, timeframe_minutes):
    """Bulk insert into stock_candle_history"""
    if df.empty: return 0
    cursor = conn.cursor()
    records = []
    
    for _, row in df.iterrows():
        if pd.isna(row['close']): continue
        ts = row['timestamp'] if 'timestamp' in row else row.name
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime().replace(tzinfo=None)
            
        records.append((
            instrument_id, ts, float(row['open']), float(row['high']),
            float(row['low']), float(row['close']), int(row['volume']),
            timeframe_minutes
        ))
    
    if not records: return 0
        
    try:
        args_str = ','.join(cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in records)
        cursor.execute(f"""
            INSERT INTO stock_candle (instrument_id, candle_ts, open, high, low, close, volume, timeframe)
            VALUES {args_str}
            ON CONFLICT (instrument_id, timeframe, candle_ts) DO NOTHING
        """)
        conn.commit()
        return len(records)
    except Exception as e:
        conn.rollback()
        # print(f"    ! Insert Error: {e}")
        raise e

def resample_and_insert(conn, instrument_id, df_1m, target_tf_str, target_mins):
    """Resample 1m data and insert"""
    if df_1m.empty: return
    try:
        resample_df = df_1m.copy()
        resample_df.set_index('timestamp', inplace=True)
        agg_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        resampled = resample_df.resample(target_tf_str).agg(agg_dict).dropna()
        insert_candles_history(conn, instrument_id, resampled, target_mins)
    except Exception as e:
        print(f"    ! Resample {target_tf_str} error: {e}")

def get_last_candle_ts(conn, instrument_id, timeframe):
    """Get the latest candle timestamp for an instrument and timeframe"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(candle_ts) 
        FROM stock_candle 
        WHERE instrument_id = %s AND timeframe = %s
    """, (instrument_id, timeframe))
    row = cursor.fetchone()
    return row[0] if row and row[0] else None

async def process_date_range(client, symbol, instrument_key, instrument_id, start_date, end_date, conn, fetch_1m=True, fetch_long_term=False):
    """Process a specific date range, primarily for 1m and resampling"""
    
    if start_date >= end_date:
        return

    # 1. Daily (Native) - If we're doing a full catchup or today's refresh
    if fetch_long_term:
        try:
            db_last_1d = get_last_candle_ts(conn, instrument_id, 1440)
            actual_start_1d = max(start_date, db_last_1d) if db_last_1d else start_date
            
            if actual_start_1d < end_date:
                print(f"    Fetching Daily: {actual_start_1d.date()} -> {end_date.date()}")
                df = await client.get_historical_data(symbol, instrument_key, actual_start_1d, end_date, "day")
                if not df.empty:
                    print(f"    Fetched {len(df)} daily candles for {symbol}")
                    insert_candles_history(conn, instrument_id, df, 1440)
        except Exception as e:
            print(f"    ! Daily fetch error for {symbol}: {e}")

        try:
            # Week/Month
            db_last_week = get_last_candle_ts(conn, instrument_id, 10080)
            actual_start_week = max(start_date, db_last_week) if db_last_week else start_date
            if actual_start_week < end_date:
                df_week = await client.get_historical_data(symbol, instrument_key, actual_start_week, end_date, "week")
                if not df_week.empty:
                    print(f"    Fetched {len(df_week)} weekly candles for {symbol}")
                    insert_candles_history(conn, instrument_id, df_week, 10080)
            
            db_last_month = get_last_candle_ts(conn, instrument_id, 43200)
            actual_start_month = max(start_date, db_last_month) if db_last_month else start_date
            if actual_start_month < end_date:
                df_month = await client.get_historical_data(symbol, instrument_key, actual_start_month, end_date, "month")
                if not df_month.empty:
                    print(f"    Fetched {len(df_month)} monthly candles for {symbol}")
                    insert_candles_history(conn, instrument_id, df_month, 43200)
        except Exception as e:
            print(f"    ! Weekly/Monthly fetch error for {symbol}: {e}")

    # 3. Intraday (1minute) -> Resample
    if fetch_1m:
        try:
            db_last_1m = get_last_candle_ts(conn, instrument_id, 1)
            actual_start_1m = max(start_date, db_last_1m) if db_last_1m else start_date

            if actual_start_1m < end_date:
                print(f"    Fetching 1m: {actual_start_1m} -> {end_date}")
                df_1m = await client.get_historical_data(symbol, instrument_key, actual_start_1m, end_date, "1minute")
                if not df_1m.empty:
                    print(f"    Fetched {len(df_1m)} 1m candles for {symbol}")
                    insert_candles_history(conn, instrument_id, df_1m, 1)
                    # Resample
                    resample_and_insert(conn, instrument_id, df_1m, '3T', 3)
                    resample_and_insert(conn, instrument_id, df_1m, '5T', 5)
                    resample_and_insert(conn, instrument_id, df_1m, '15T', 15)
                    resample_and_insert(conn, instrument_id, df_1m, '30T', 30)
                    resample_and_insert(conn, instrument_id, df_1m, '1H', 60)
        except Exception as e:
            print(f"    ! 1m fetch error for {symbol}: {e}")

async def process_symbol(client, symbol):
    print(f"\nProcessing {symbol}...")
    update_status(symbol, 'PROCESSING')
    
    conn = None # Initialize conn to None
    try:
        # Improved Resolution for Symbols and Indices
        instrument_id = None
        # 1. Try common Indices first (NIFTY 50, NIFTY BANK)
        if 'NIFTY' in symbol or 'INDIA VIX' in symbol or 'MCX' in symbol:
             instrument_id = resolve_instrument_id(symbol, exchange='NSE_INDEX')
        
        # 2. Try NSE Equity
        if not instrument_id:
             instrument_id = resolve_instrument_id(symbol, exchange='NSE')
        
        # 3. Try Generic
        if not instrument_id:
             instrument_id = resolve_instrument_id(symbol)
             
        if not instrument_id:
            print(f"  ! Skipping {symbol}: Instrument ID not found")
            update_status(symbol, 'SKIPPED', "Instrument ID not found")
            return

        info = get_instrument_info(instrument_id)
        if not info:
            print(f"  ! Skipping {symbol}: Instrument Info not found")
            update_status(symbol, 'SKIPPED', "Instrument Info not found")
            return
            
        instrument_key = info.instrument_key
        print(f"  Resolved: {instrument_key} (ID: {instrument_id})")

        conn = get_connection()
        
        start_history = datetime(2022, 1, 1)
        end_now = datetime.now()
        
        # 1. Fetch Long-term
        await process_date_range(client, symbol, instrument_key, instrument_id, start_history, end_now, conn, fetch_1m=False, fetch_long_term=True)
        
        # 2. Fetch 1m
        db_last_1m = get_last_candle_ts(conn, instrument_id, 1)
        start_1m = db_last_1m if db_last_1m else start_history
        if not db_last_1m:
            one_year_ago = end_now - timedelta(days=365)
            start_1m = max(start_1m, one_year_ago)

        curr = start_1m
        while curr < end_now:
            chunk_end = curr + relativedelta(months=1)
            if chunk_end > end_now:
                chunk_end = end_now
            
            # print(f"  1m Chunk: {curr} -> {chunk_end}")
            await process_date_range(client, symbol, instrument_key, instrument_id, curr, chunk_end, conn, fetch_1m=True, fetch_long_term=False)
            
            curr = chunk_end
            await asyncio.sleep(0.5) 
            
        update_status(symbol, 'COMPLETED')
        print(f"  ✓ {symbol} Completed")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ✗ {symbol} Failed: {e}")
        update_status(symbol, 'FAILED', str(e))

async def main():
    print("=" * 60)
    print("Starting History Incremental ETL (Jan 2022 - Today)")
    print("Target: stock_candle")
    print("=" * 60)
    
    init_job_status()
    client = get_upstox_client()
    
    while True:
        symbol = get_next_symbol()
        if not symbol:
            print("No more pending symbols. Job Complete.")
            break
            
        await process_symbol(client, symbol)
        
        # Pause to avoid rate limits / circuit breaker
        await asyncio.sleep(2)
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
