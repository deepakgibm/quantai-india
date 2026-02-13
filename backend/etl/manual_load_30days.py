
import os
import sys
import time
import asyncio
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]

# Add backend directory to path
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

# Explicit NIFTY 500 List
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
    "HONASA", "HONAUT", "HUDCO", "NCC", "HYUNDAI", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDFCFIRSTB",
    "IFCI", "IIFL", "INOXINDIA", "IRB", "IRCON", "ITCHOTELS", "ITC", "ITI", "INDGN", "INDIACEM",
    "INDIAMART", "INDIANB", "IEX", "INDHOTEL", "IOC", "IOB", "IRCTC", "IRFC", "IREDA", "IGL",
    "INDUSTOWER", "INDUSINDBK", "NAUKRI", "INOXWIND", "INTELLECT", "INDIGO", "IGIL", "IKS", "IPCALAB",
    "JBCHEPHARM", "JKCEMENT", "JBMA", "JKTYRE", "JMFINANCIL", "JSWENERGY", "JSWINFRA", "JSWSTEEL", "JPPOWER",
    "J&KBANK", "JINDALSAW", "JSL", "JINDALSTEL", "JIOFIN", "JUBLFOOD", "JUBLINGREA", "JUBLPHARMA", "JWL",
    "JYOTHYLAB", "NHPC", "JYOTICNC", "KPRMILL", "KEI", "KPITTECH", "KSB", "KAJARIACER", "KPIL", "KALYANKJIL",
    "KARURVYSYA", "KAYNES", "KEC", "KFINTECH", "KIRLOSBROS", "KIRLOSENG", "KIMS", "LTF", "LTTS", "LICHSGFIN",
    "LTFOODS", "LTIM", "LT", "LATENTVIEW", "LAURUSLABS", "THELEELA", "LEMONTREE", "LICI", "LINDEINDIA",
    "LLOYDSME", "LODHA", "LUPIN", "MMTC", "MRF", "MGL", "MAHSCOOTER", "MAHSEAMLES", "M&MFIN", "M&M",
    "MRPL", "MANKIND", "MARICO", "MARUTI", "MFSL", "MAXHEALTH", "MAZDOCK", "METROPOLIS", "MINDACORP",
    "MSUMI", "MOTILALOFS", "MPHASIS", "MUTHOOTFIN", "NATCOPHARM", "NBCC", "NLCINDIA", "NMDC", "NSLNISP",
    "NTPCGREEN", "NTPC", "NH", "NATIONALUM", "NAVA", "NAVINFLUOR", "NESTLEIND", "NUVAMA", "NUVOCO",
    "OBEROIRLTY", "ONGC", "OIL", "OLECTRA", "PIIND", "PNBHOUSING", "PVRINOX", "PAGEIND", "PERSISTENT",
    "PETRONET", "PHOENIXLTD", "PIDILITIND", "POLYMED", "POLYCAB", "POONAWALLA", "PFC", "POWERGRID",
    "PRAJIND", "PRESTIGE", "PGHH", "PNB", "RBLBANK", "RECLTD", "RADICO", "RVNL", "REDINGTON", "RELIANCE",
    "SBFC", "SBICARD", "SBILIFE", "SJVN", "SKFINDIA", "SRF", "MOTHERSON", "SCHAEFFLER", "SCHNEIDER",
    "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SOBHA", "SOLARINDS", "SONACOMS", "STARHEALTH", "SBIN", "SAIL",
    "SUNPHARMA", "SUNTV", "SUNDARMFIN", "SUNDRMFAST", "SUPREMEIND", "SYNGENE", "TVSMOTOR", "TATACHEM",
    "TATACOMM", "TATACONSUM", "TATAELXSI", "TATAINVEST", "TATAPOWER", "TATASTEEL", "TECHM", "TECHNOE",
    "RAMCOCEM", "THERMAX", "TIMKEN", "TITAN", "TORNTPHARM", "TORNTPOWER", "TRENT", "TRIDENT", "TRITURBINE",
    "TIINDIA", "UCOBANK", "UPL", "UTIAMC", "ULTRACEMCO", "UNIONBANK", "UBL", "USHAMART", "VGUARD", "VBL",
    "VEDL", "VIJAYA", "VOLTAS", "WELCORP", "WELSPUNLIV", "WHIRLPOOL", "WIPRO", "WOCKPHARMA", "YESBANK",
    "ZEEL", "ZENTEC", "ZENSARTECH", "ZYDUSLIFE", "INFY", "TCS", "NIFTY 50", "BANK NIFTY", "INDIA VIX",
    "MCX", "KOTAKBANK"
]

# DB Config
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'admin',
    'database': 'quantai'
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def insert_candles(conn, instrument_id, df, timeframe_minutes):
    """Bulk insert candles for a given timeframe"""
    if df.empty: return 0
    
    cursor = conn.cursor()
    records = []
    
    for _, row in df.iterrows():
        # Handle nan/missing
        if pd.isna(row['close']): continue
        
        # Timestamp handling
        ts = row['timestamp'] if 'timestamp' in row else row.name
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime().replace(tzinfo=None)
            
        records.append((
            instrument_id,
            ts,
            float(row['open']),
            float(row['high']),
            float(row['low']),
            float(row['close']),
            int(row['volume']),
            timeframe_minutes
        ))
    
    if not records: return 0
        
    try:
        args_str = ','.join(cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in records)
        
        cursor.execute("BEGIN")
        cursor.execute(f"""
            INSERT INTO stock_candle (instrument_id, candle_ts, open, high, low, close, volume, timeframe)
            VALUES {args_str}
            ON CONFLICT (instrument_id, timeframe, candle_ts) DO NOTHING
        """)
        conn.commit()
        return len(records)
    except Exception as e:
        conn.rollback()
        print(f"    ! Insert Error ({timeframe_minutes}m): {e}")
        return 0

def resample_and_insert(conn, instrument_id, df_1m, target_tf_str, target_mins):
    """Resample 1m data to target timeframe and insert."""
    try:
        # Prepare for resampling
        resample_df = df_1m.copy()
        resample_df.set_index('timestamp', inplace=True)
        
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # Resample
        resampled = resample_df.resample(target_tf_str).agg(agg_dict).dropna()
        
        # Insert
        count = insert_candles(conn, instrument_id, resampled, target_mins)
        if count > 0:
            print(f"  + {target_tf_str} ({target_mins}m): {count} candles (Resampled from 1m)")
            
    except Exception as e:
        print(f"    ! Resample Error ({target_tf_str}): {e}")

async def load_data_for_symbol(client, symbol: str, days: int = 30):
    print(f"\nProcessing {symbol}...")
    
    # 1. Resolve Instrument
    instrument_id = None
    instrument_key = None
    try:
        instrument_id = resolve_instrument_id(symbol, exchange='NSE')
        if instrument_id:
            info = get_instrument_info(instrument_id)
            if info:
                instrument_key = info.instrument_key
    except:
        pass
        
    if not instrument_id or not instrument_key:
        print(f"  ⚠ Skipping {symbol}: Instrument ID/Key not found")
        return

    conn = get_connection()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # --- 1. Fetch and Insert DAILY (Native) ---
    try:
        df_day = await client.get_historical_data(
            symbol=symbol, 
            instrument_key=instrument_key,
            from_date=start_date, 
            to_date=end_date, 
            interval="day"
        )
        if not df_day.empty:
            count = insert_candles(conn, instrument_id, df_day, 1440)
            print(f"  + 1d: {count} candles (Native)")
        else:
            print(f"  - 1d: No data")
    except Exception as e:
        print(f"  ! 1d Error: {e}")
    
    # Pause
    await asyncio.sleep(0.5)

    # --- 2. Fetch 1-MINUTE (Native) ---
    df_1m = pd.DataFrame()
    try:
        df_1m = await client.get_historical_data(
            symbol=symbol, 
            instrument_key=instrument_key,
            from_date=start_date, 
            to_date=end_date, 
            interval="1minute"
        )
        if not df_1m.empty:
             print(f"  ✓ Fetched {len(df_1m)} 1m candles for resampling")
        else:
             print(f"  - 1m: No data (Skipping derived TFs)")
    except Exception as e:
        print(f"  ! 1m Error: {e}")
        
    # --- 3. Derived Timeframes (3m, 15m, 1h) from 1m ---
    if not df_1m.empty:
        # User Requested: 3m, 15m, 1h
        # 3m
        resample_and_insert(conn, instrument_id, df_1m, '3T', 3)
        # 15m
        resample_and_insert(conn, instrument_id, df_1m, '15T', 15)
        # 1h (60m)
        resample_and_insert(conn, instrument_id, df_1m, '1H', 60)
    
    conn.close()

async def main():
    print("=" * 60)
    print(f"Starting Upstox Historical Loader (Resampling Mode)")
    print(f"Target: Daily + 3m/15m/1h (derived from 1m)")
    print(f"Symbols: {len(NIFTY_500_SYMBOLS)}")
    print("=" * 60)
    
    client = get_upstox_client()
    
    for i, symbol in enumerate(NIFTY_500_SYMBOLS):
        try:
            await load_data_for_symbol(client, symbol)
            
            if (i + 1) % 5 == 0:
                print("  [Pausing 1s...]")
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n⚠ Stopped by user")
            break
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
