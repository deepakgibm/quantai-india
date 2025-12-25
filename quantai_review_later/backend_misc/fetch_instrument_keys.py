"""
Fetch Nifty 200 Instrument Keys
Downloads Nifty 200 list and Upstox master instruments to generate a mapping file.
"""
import requests
import pandas as pd
import gzip
import io
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.config import settings

# URLs
NIFTY_200_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty200list.csv"
UPSTOX_MASTER_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz"

OUTPUT_FILE = "nifty200_instruments.json"

def fetch_nifty_200_symbols():
    local_file = "nifty200.csv"
    if os.path.exists(local_file):
        print(f"Using local file {local_file}...")
        try:
            df = pd.read_csv(local_file)
            if "Symbol" in df.columns:
                return df["Symbol"].tolist()
            elif "symbol" in df.columns:
                return df["symbol"].tolist()
            else:
                print(f"Columns found: {df.columns}")
                return []
        except Exception as e:
            print(f"Error reading local Nifty 200 file: {e}")
            
    print(f"Downloading Nifty 200 list from {NIFTY_200_URL}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(NIFTY_200_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        df = pd.read_csv(io.StringIO(response.text))
        if "Symbol" in df.columns:
            return df["Symbol"].tolist()
        elif "symbol" in df.columns:
            return df["symbol"].tolist()
        else:
            print(f"Columns found: {df.columns}")
            return []
    except Exception as e:
        print(f"Error fetching Nifty 200 list: {e}")
        print("Falling back to Nifty 100 from config...")
        return settings.NIFTY_100_SYMBOLS

def fetch_upstox_instruments():
    local_file = "nse.csv.gz"
    if os.path.exists(local_file):
        print(f"Using local file {local_file}...")
        try:
            with gzip.open(local_file, 'rt') as f:
                df = pd.read_csv(f)
            
            print(f"Loaded {len(df)} rows from Upstox file.")
            if 'instrument_type' in df.columns:
                print(f"Instrument types: {df['instrument_type'].unique()}")
                df = df[df['instrument_type'] == 'EQUITY']
                print(f"Filtered to {len(df)} EQUITY rows.")
                return df
            else:
                print(f"Column 'instrument_type' not found. Columns: {df.columns}")
                return pd.DataFrame()
        except Exception as e:
            print(f"Error reading local Upstox file: {e}")

    print(f"Downloading Upstox master list from {UPSTOX_MASTER_URL}...")
    try:
        response = requests.get(UPSTOX_MASTER_URL)
        response.raise_for_status()
        
        with gzip.open(io.BytesIO(response.content), 'rt') as f:
            df = pd.read_csv(f)
            
        # Filter for EQ
        df = df[df['instrument_type'] == 'EQUITY']
        return df
    except Exception as e:
        print(f"Error fetching Upstox master list: {e}")
        return pd.DataFrame()

def main():
    # 1. Get Nifty 200 Symbols
    nifty_symbols = fetch_nifty_200_symbols()
    if not nifty_symbols:
        print("Failed to get Nifty 200 symbols. Using fallback list from config if available (not implemented).")
        # Fallback to Nifty 100 from config if needed, but let's hope this works
        # Or hardcode top 200? No.
        return

    print(f"Found {len(nifty_symbols)} Nifty 200 symbols.")
    
    # 2. Get Upstox Instruments
    upstox_df = fetch_upstox_instruments()
    if upstox_df.empty:
        print("Failed to get Upstox instruments.")
        return
        
    print(f"Found {len(upstox_df)} Upstox EQ instruments.")
    
    # 3. Match
    mapping = []
    missing = []
    
    # Create lookup for Upstox
    # Upstox 'tradingsymbol' usually matches NSE symbol
    upstox_map = dict(zip(upstox_df['tradingsymbol'], upstox_df['instrument_key']))
    
    for sym in nifty_symbols:
        # NSE symbols might need cleaning? usually they match
        if sym in upstox_map:
            mapping.append((sym, upstox_map[sym]))
        else:
            missing.append(sym)
            
    print(f"Matched {len(mapping)} symbols.")
    if missing:
        print(f"Missing {len(missing)} symbols: {missing}")
        
    # 4. Save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(mapping, f, indent=2)
        
    print(f"Saved mapping to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
