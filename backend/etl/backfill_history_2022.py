
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
    "360ONE", "3MINDIA", "ABB", "ACC", "ACMESOLAR", "AIAENG", "APLAPOLLO", "AUBANK", "AWL", "AADHARHFC",
    "AARTIIND", "AAVAS", "ABBOTINDIA", "ACE", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER",
    "ATGL", "ABCAPITAL", "ABFRL", "ABLBL", "ABREL", "ABSLAMC", "AEGISLOG", "AEGISVOPAK", "AFCONS", "AFFLE",
    "AJANTPHARM", "AKUMS", "AKZOINDIA", "APLLTD", "ALKEM", "ALKYLAMINE", "ALOKINDS", "ARE&M", "AMBER",
    "AMBUJACEM", "ANANDRATHI", "ANANTRAJ", "ANGELONE", "APARINDS", "APOLLOHOSP", "APOLLOTYRE", "APTUS",
    "ASAHIINDIA", "ASHOKLEY", "ASIANPAINT", "ASTERDM", "ASTRAZEN", "ASTRAL", "ATHERENERG", "ATUL", "AUROPHARMA",
    "AIIL", "DMART", "AXISBANK", "BASF", "BEML", "BLS", "BSE", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV",
    "BAJAJHLDNG", "BAJAJHFL", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "MAHABANK",
    "BATAINDIA", "BAYERCROP", "BERGEPAINT", "BDL", "BEL", "BHARATFORG", "BHEL", "BPCL", "BHARTIARTL",
    "BHARTIHEXA", "BIKAJI", "BIOCON", "BSOFT", "BLUEDART", "BLUEJET", "BLUESTARCO", "BBTC", "BOSCHLTD",
    "FIRSTCRY", "BRIGADE", "BRITANNIA", "MAPMYINDIA", "CCL", "CESC", "CGPOWER", "CRISIL", "CAMPUS",
    "CANFINHOME", "CANBK", "CAPLIPOINT", "CGCL", "CARBORUNIV", "CASTROLIND", "CEATLTD", "CENTRALBK", "CDSL",
    "CENTURYPLY", "CERA", "CHALET", "CHAMBLFERT", "CHENNPETRO", "CHOICEIN", "CHOLAHLDNG", "CHOLAFIN", "CIPLA",
    "CUB", "CLEAN", "COALINDIA", "COCHINSHIP", "COFORGE", "COHANCE", "COLPAL", "CAMS", "CONCORDBIO", "CONCOR",
    "COROMANDEL", "CRAFTSMAN", "CREDITACC", "CROMPTON", "CUMMINSIND", "CYIENT", "DCMSHRIRAM", "DLF", "DOMS",
    "DABUR", "DALBHARAT", "DATAPATTNS", "DEEPAKFERT", "DEEPAKNTR", "DELHIVERY", "DEVYANI", "DIVISLAB", "DIXON",
    "AGARWALEYE", "LALPATHLAB", "DRREDDY", "EIDPARRY", "EIHOTEL", "EICHERMOT", "ELECON", "ELGIEQUIP",
    "EMAMILTD", "EMCURE", "ENDURANCE", "ENGINERSIN", "ERIS", "ESCORTS", "ETERNAL", "EXIDEIND", "NYKAA",
    "FEDERALBNK", "FACT", "FINCABLES", "FINPIPE", "FSL", "FIVESTAR", "FORCEMOT", "FORTIS", "GAIL", "GVT&D",
    "GMRAIRPORT", "GRSE", "GICRE", "GILLETTE", "GLAND", "GLAXO", "GLENMARK", "MEDANTA", "GODIGIT", "GPIL",
    "GODFRYPHLP", "GODREJAGRO", "GODREJCP", "GODREJIND", "GODREJPROP", "GRANULES", "GRAPHITE", "GRASIM",
    "GRAVITA", "GESHIP", "FLUOROCHEM", "GUJGASLTD", "GMDCLTD", "GSPL", "HEG", "HBLENGINE", "HCLTECH",
    "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HFCL", "HAPPSTMNDS", "HAVELLS", "HEROMOTOCO", "HEXT", "HSCL",
    "HINDALCO", "HAL", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "HINDZINC", "POWERINDIA", "HOMEFIRST",
    "HONASA", "HONAUT", "HUDCO", "NCC", "HYUNDAI", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDBI",
    "IDFCFIRSTB", "IFCI", "IIFL", "INOXINDIA", "IRB", "IRCON", "ITCHOTELS", "ITC", "ITI", "INDGN",
    "INDIACEM", "INDIAMART", "INDIANB", "IEX", "INDHOTEL", "IOC", "IOB", "IRCTC", "IRFC", "IREDA", "IGL",
    "INDUSTOWER", "INDUSINDBK", "NAUKRI", "INOXWIND", "INTELLECT", "INDIGO", "IGIL", "IKS", "IPCALAB",
    "JBCHEPHARM", "JKCEMENT", "JBMA", "JKTYRE", "JMFINANCIL", "JSWENERGY", "JSWINFRA", "JSWSTEEL", "JPPOWER",
    "J&KBANK", "JINDALSAW", "JSL", "JINDALSTEL", "JIOFIN", "JUBLFOOD", "JUBLINGREA", "JUBLPHARMA", "JWL",
    "JYOTHYLAB", "NHPC", "JYOTICNC", "KPRMILL", "KEI", "KPITTECH", "KSB", "KAJARIACER", "KPIL", "KALYANKJIL",
    "KARURVYSYA", "KAYNES", "KEC", "KFINTECH", "KIRLOSBROS", "KIRLOSENG", "KIMS", "LTF", "LTTS", "LICHSGFIN",
    "LTFOODS", "LTIM", "LT", "LATENTVIEW", "LAURUSLABS", "THELEELA", "LEMONTREE", "LICI", "LINDEINDIA",
    "LLOYDSME", "LODHA", "LUPIN", "MMTC", "MRF", "MGL", "MAHSCOOTER", "MAHSEAMLES", "M&MFIN", "M&M",
    "MANAPPURAM", "MRPL", "MANKIND", "MARICO", "MARUTI", "MFSL", "MAXHEALTH", "MAZDOCK", "METROPOLIS",
    "MINDACORP", "MSUMI", "MOTILALOFS", "MPHASIS", "MUTHOOTFIN", "NATCOPHARM", "NBCC", "NLCINDIA", "NMDC",
    "NSLNISP", "NTPCGREEN", "NTPC", "NH", "NATIONALUM", "NAVA", "NAVINFLUOR", "NESTLEIND", "NETWEB",
    "NEULANDLAB", "NEWGEN", "NAM-INDIA", "NIVABUPA", "NUVAMA", "NUVOCO", "OBEROIRLTY", "ONGC", "OIL",
    "OLAELEC", "OLECTRA", "PAYTM", "ONESOURCE", "OFSS", "POLICYBZR", "PCBL", "PGEL", "PIIND", "PNBHOUSING",
    "PTCIL", "PVRINOX", "PAGEIND", "PATANJALI", "PERSISTENT", "PETRONET", "PFIZER", "PHOENIXLTD",
    "PIDILITIND", "PPLPHARMA", "POLYMED", "POLYCAB", "POONAWALLA", "PFC", "POWERGRID", "PRAJIND", "PREMIERENE",
    "PRESTIGE", "PGHH", "PNB", "RRKABEL", "RBLBANK", "RECLTD", "RHIM", "RITES", "RADICO", "RVNL", "RAILTEL",
    "RAINBOW", "RKFORGE", "RCF", "REDINGTON", "RELIANCE", "RELINFRA", "RPOWER", "SBFC", "SBICARD", "SBILIFE",
    "SJVN", "SKFINDIA", "SRF", "SAGILITY", "SAILIFE", "SAMMAANCAP", "MOTHERSON", "SAPPHIRE", "SARDAEN",
    "SAREGAMA", "SCHAEFFLER", "SCHNEIDER", "SCI", "SHREECEM", "SHRIRAMFIN", "SHYAMMETL", "ENRIN", "SIEMENS",
    "SIGNATURE", "SOBHA", "SOLARINDS", "SONACOMS", "SONATSOFTW", "STARHEALTH", "SBIN", "SAIL", "SUMICHEM",
    "SUNPHARMA", "SUNTV", "SUNDARMFIN", "SUNDRMFAST", "SUPREMEIND", "SUZLON", "SWANCORP", "SWIGGY", "SYNGENE",
    "SYRMA", "TBOTEK", "TVSMOTOR", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAELXSI", "TATAINVEST", "TMPV",
    "TATAPOWER", "TATASTEEL", "TATATECH", "TTML", "TECHM", "TECHNOE", "TEJASNET", "NIACL", "RAMCOCEM",
    "THERMAX", "TIMKEN", "TITAGARH", "TITAN", "TORNTPHARM", "TORNTPOWER", "TARIL", "TRENT", "TRIDENT",
    "TRIVENI", "TRITURBINE", "TIINDIA", "UCOBANK", "UNOMINDA", "UPL", "UTIAMC", "ULTRACEMCO", "UNIONBANK",
    "UBL", "UNITDSPR", "USHAMART", "VGUARD", "DBREALTY", "VTL", "VBL", "MANYAVAR", "VEDL", "VENTIVE",
    "VIJAYA", "VMM", "IDEA", "VOLTAS", "WAAREEENER", "WELCORP", "WELSPUNLIV", "WHIRLPOOL", "WIPRO",
    "WOCKPHARMA", "YESBANK", "ZFCVINDIA", "ZEEL", "ZENTEC", "ZENSARTECH", "ZYDUSLIFE", "ECLERX", "INFY", "TCS",
    "NIFTY 50", "BANK NIFTY", "INDIA VIX", "MCX", "DUMMYHDLVR", "KOTAKBANK"
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
            INSERT INTO stock_candle_history (instrument_id, candle_ts, open, high, low, close, volume, timeframe)
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

async def process_date_range(client, symbol, instrument_key, instrument_id, start_date, end_date, conn, final_run=False):
    """Process a specific date range for all timeframes"""
    
    # 1. Daily (Native)
    try:
        df = await client.get_historical_data(symbol, instrument_key, start_date, end_date, "day")
        if not df.empty:
            insert_candles_history(conn, instrument_id, df, 1440)
    except Exception as e:
        print(f"    ! Daily fetch error: {e}")

    # 2. Week/Month (Native) - Only if final run (to avoid overlap duplicates redundancy, though safe ON CONFLICT)
    # Actually, fetching 4 years of weekly data is single call.
    if final_run:
        try:
            df_week = await client.get_historical_data(symbol, instrument_key, start_date, end_date, "week")
            if not df_week.empty:
                # 1 week = 10080 mins approx, but varies. Let's use custom ID or 10080.
                # Project uses minutes. 1 week ~ 5 days * 375 mins? No, typically 7 days.
                # Let's map week -> 10080 (7*24*60).
                insert_candles_history(conn, instrument_id, df_week, 10080)
            
            df_month = await client.get_historical_data(symbol, instrument_key, start_date, end_date, "month")
            if not df_month.empty:
                # 1 month -> 43200 (30*24*60) approx
                insert_candles_history(conn, instrument_id, df_month, 43200)
        except Exception:
            pass

    # 3. Intraday (1minute) -> Resample
    # Fetch in chunks of 30 days to be safe?
    # Upstox V2 limit: For 1minute, assumes 1 month max?
    # Let's try fetching the chunk range passed to function.
    try:
        df_1m = await client.get_historical_data(symbol, instrument_key, start_date, end_date, "1minute")
        if not df_1m.empty:
            insert_candles_history(conn, instrument_id, df_1m, 1)
            # Resample
            resample_and_insert(conn, instrument_id, df_1m, '3T', 3)
            resample_and_insert(conn, instrument_id, df_1m, '5T', 5)
            resample_and_insert(conn, instrument_id, df_1m, '15T', 15)
            resample_and_insert(conn, instrument_id, df_1m, '30T', 30)
            resample_and_insert(conn, instrument_id, df_1m, '1H', 60)
        else:
             # If 1m is not available for historical dates (e.g. 2022), check 30m?
             # Upstox says 30m available for 1 year. 2022 is > 1 year.
             # So we might ONLY get Daily/Weekly/Monthly for 2022.
             # Just in case, try 30m Native if 1m failed?
             if not df_1m.empty: pass # Done
             else:
                 pass # Skip
    except Exception as e:
        print(f"    ! 1m fetch error: {e}")

async def process_symbol(client, symbol):
    print(f"\nProcessing {symbol}...")
    update_status(symbol, 'PROCESSING')
    
    try:
        # Resolve ID
        instrument_id = resolve_instrument_id(symbol, exchange='NSE')
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

        conn = get_connection()
        
        # Date Range: Jan 1, 2022 to Today
        start_overall = datetime(2022, 1, 1)
        end_overall = datetime.now()
        
        # Iterate in 1-month chunks for Intraday safety
        curr = start_overall
        while curr < end_overall:
            chunk_end = curr + relativedelta(months=1)
            if chunk_end > end_overall:
                chunk_end = end_overall
            
            print(f"  Chunk: {curr.date()} -> {chunk_end.date()}")
            
            # Process this chunk
            final_run = (chunk_end == end_overall) # Fetch weekly/monthly only at end? No, fetch full range once.
            
            # Actually, weekly/monthly can be fetched for FULL range (Jan 2022-Now) in one go (supports 10 years).
            # Intraday 1m/30m supports < 1 year.
            # So I should fetch Weekly/Monthly ONCE.
            # And loop for Intraday.
            
            await process_date_range(client, symbol, instrument_key, instrument_id, curr, chunk_end, conn, final_run=False)
            
            curr = chunk_end
            await asyncio.sleep(0.5) # Gentle on rate limits
            
        # Fetch Long-term intervals (Week/Month) for full range
        await process_date_range(client, symbol, instrument_key, instrument_id, start_overall, end_overall, conn, final_run=True)
            
        conn.close()
        update_status(symbol, 'COMPLETED')
        print(f"  ✓ {symbol} Completed")
        
    except Exception as e:
        print(f"  ✗ {symbol} Failed: {e}")
        update_status(symbol, 'FAILED', str(e))

async def main():
    print("=" * 60)
    print("Starting History Backfill (Jan 2022 - Today)")
    print("Target: stock_candle_history")
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
