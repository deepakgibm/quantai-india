"""
Nifty 500 Historical Data ETL Job with Checkpoint/Resume
=========================================================
Loads daily OHLCV data from 2022-01-03 to today for all Nifty 500 stocks.
Features:
- Checkpoint/Resume: Saves progress to JSON file, resumes from last successful symbol
- Rate limiting: Respects yfinance API limits
- Transaction safety: Commits after each symbol
- Duplicate handling: Skips existing records
- Progress tracking: Shows detailed progress and statistics
"""

import json
import os
import time
import psycopg2
import pandas as pd
import yfinance as yf
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

# Checkpoint file location
CHECKPOINT_FILE = Path(__file__).parent / "nifty500_etl_checkpoint.json"

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'admin',
    'database': 'quantai'
}

# Date range configuration
START_DATE = "2022-01-03"
END_DATE = datetime.now().strftime("%Y-%m-%d")

# Complete Nifty 500 Symbol List
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


class Checkpoint:
    """Manages checkpoint/resume state for the ETL job."""
    
    def __init__(self, filepath: Path = CHECKPOINT_FILE):
        self.filepath = filepath
        self.data = self._load()
    
    def _load(self) -> Dict:
        """Load checkpoint from file."""
        if self.filepath.exists():
            with open(self.filepath, 'r') as f:
                return json.load(f)
        return {
            "job_id": None,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "last_completed_symbol": None,
            "last_completed_index": -1,
            "total_symbols": len(NIFTY_500_SYMBOLS),
            "completed_symbols": [],
            "failed_symbols": [],
            "stats": {
                "total_records": 0,
                "inserted": 0,
                "skipped": 0,
                "errors": 0
            },
            "started_at": None,
            "last_updated": None
        }
    
    def save(self):
        """Save checkpoint to file."""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def mark_completed(self, symbol: str, index: int, records_inserted: int):
        """Mark a symbol as completed."""
        self.data["last_completed_symbol"] = symbol
        self.data["last_completed_index"] = index
        self.data["completed_symbols"].append(symbol)
        self.data["stats"]["inserted"] += records_inserted
        self.save()
    
    def mark_failed(self, symbol: str, error: str):
        """Mark a symbol as failed."""
        self.data["failed_symbols"].append({"symbol": symbol, "error": error})
        self.data["stats"]["errors"] += 1
        self.save()
    
    def get_resume_index(self) -> int:
        """Get the index to resume from."""
        return self.data["last_completed_index"] + 1
    
    def reset(self):
        """Reset checkpoint for a fresh start."""
        if self.filepath.exists():
            os.remove(self.filepath)
        self.data = self._load()
        self.data["job_id"] = f"nifty500_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.data["started_at"] = datetime.now().isoformat()
        self.save()


class Nifty500ETL:
    """ETL Job for loading Nifty 500 historical data."""
    
    def __init__(self, checkpoint: Checkpoint):
        self.checkpoint = checkpoint
        self.conn = None
    
    def get_connection(self):
        """Get database connection."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def fix_sequence(self):
        """Fix the PostgreSQL sequence for stock_data table."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM stock_data")
        max_id = cursor.fetchone()[0] or 0
        cursor.execute(f"ALTER SEQUENCE stock_data_id_seq RESTART WITH {max_id + 1}")
        conn.commit()
        cursor.close()
        print(f"✓ Sequence fixed (next ID: {max_id + 1})")
    
    def load_symbol_data(self, symbol: str, start_date: str, end_date: str) -> Tuple[bool, int]:
        """Load data for a single symbol using yfinance."""
        yf_symbol = f"{symbol}.NS"
        records_inserted = 0
        
        try:
            # Fetch data from yfinance
            ticker = yf.Ticker(yf_symbol)
            data = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if data.empty:
                return (False, 0)
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
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
                    self.checkpoint.data["stats"]["skipped"] += 1
                    continue
                
                # Insert new record
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
            if self.conn:
                self.conn.rollback()
            raise e
    
    def run(self, fresh_start: bool = False):
        """Run the ETL job."""
        print("\n" + "=" * 70)
        print("NIFTY 500 HISTORICAL DATA ETL JOB")
        print("=" * 70)
        print(f"Date Range: {START_DATE} to {END_DATE}")
        print(f"Total Symbols: {len(NIFTY_500_SYMBOLS)}")
        print("=" * 70 + "\n")
        
        # Handle checkpoint
        if fresh_start:
            print("Starting fresh (clearing checkpoint)...")
            self.checkpoint.reset()
        else:
            resume_index = self.checkpoint.get_resume_index()
            if resume_index > 0:
                print("Resuming from checkpoint...")
                print(f"  Last completed: {self.checkpoint.data['last_completed_symbol']}")
                print(f"  Progress: {resume_index}/{len(NIFTY_500_SYMBOLS)} symbols")
                print(f"  Records inserted so far: {self.checkpoint.data['stats']['inserted']}")
            else:
                self.checkpoint.data["job_id"] = f"nifty500_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.checkpoint.data["started_at"] = datetime.now().isoformat()
                self.checkpoint.save()
        
        print(f"\nJob ID: {self.checkpoint.data['job_id']}")
        print("\n" + "-" * 70)
        
        # Fix sequence before starting
        self.fix_sequence()
        
        start_index = self.checkpoint.get_resume_index()
        symbols_to_process = NIFTY_500_SYMBOLS[start_index:]
        
        start_time = time.time()
        
        for i, symbol in enumerate(symbols_to_process):
            actual_index = start_index + i
            print(f"[{actual_index + 1}/{len(NIFTY_500_SYMBOLS)}] {symbol}...", end=" ", flush=True)
            
            try:
                success, records = self.load_symbol_data(symbol, START_DATE, END_DATE)
                
                if success:
                    self.checkpoint.mark_completed(symbol, actual_index, records)
                    print(f"✓ ({records} records)")
                else:
                    self.checkpoint.mark_failed(symbol, "No data available")
                    print("✗ (no data)")
                    
            except Exception as e:
                self.checkpoint.mark_failed(symbol, str(e))
                print(f"✗ (error: {e})")
            
            # Rate limiting
            if (actual_index + 1) % 25 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / (i + 1)
                remaining = len(symbols_to_process) - (i + 1)
                eta = remaining * avg_time / 60
                
                print(f"\n  --- Progress: {actual_index + 1}/{len(NIFTY_500_SYMBOLS)} | ETA: {eta:.1f} minutes ---")
                print("  [Pausing to avoid rate limits...]")
                time.sleep(3)
            else:
                time.sleep(0.5)
        
        # Final summary
        elapsed_total = time.time() - start_time
        stats = self.checkpoint.data["stats"]
        
        print("\n" + "=" * 70)
        print("ETL JOB COMPLETE")
        print("=" * 70)
        print(f"Job ID: {self.checkpoint.data['job_id']}")
        print(f"Duration: {elapsed_total / 60:.1f} minutes")
        print(f"Symbols Completed: {len(self.checkpoint.data['completed_symbols'])}")
        print(f"Symbols Failed: {len(self.checkpoint.data['failed_symbols'])}")
        print(f"Records Inserted: {stats['inserted']}")
        print(f"Records Skipped (duplicates): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print("=" * 70 + "\n")
        
        if self.conn:
            self.conn.close()


def main():
    """Main entry point."""
    import sys
    
    checkpoint = Checkpoint()
    etl = Nifty500ETL(checkpoint)
    
    # Check for --fresh flag
    fresh_start = "--fresh" in sys.argv
    
    etl.run(fresh_start=fresh_start)


if __name__ == "__main__":
    main()
