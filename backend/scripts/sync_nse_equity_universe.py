import sys
import os
import pandas as pd
from sqlalchemy import text

# Add parent directory of scripts to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models_alpha import InstrumentMaster

def sync():
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "NSE_Equity_Data.csv")
    print(f"[CSV_IMPORT] Reading CSV from {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"[CSV_IMPORT] [ERROR] CSV file not found at {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    
    # Validate columns
    required_cols = ['name', 'trading_symbol', 'exchange', 'instrument_type', 'isin']
    for col in required_cols:
        if col not in df.columns:
            print(f"[CSV_IMPORT] [ERROR] Missing required column: {col}")
            return
            
    # Filter for exchange == 'NSE', instrument_type == 'EQ', valid symbol and ISIN
    df_filtered = df[
        (df['exchange'] == 'NSE') & 
        (df['instrument_type'] == 'EQ') &
        (df['trading_symbol'].notna()) &
        (df['isin'].notna())
    ].copy()
    
    # Deduplicate input dataframe to prevent processing duplicate rows in the CSV
    df_filtered.drop_duplicates(subset=['trading_symbol'], keep='first', inplace=True)
    df_filtered.drop_duplicates(subset=['isin'], keep='first', inplace=True)
    
    print(f"[CSV_IMPORT] Filtered and deduplicated to {len(df_filtered)} unique NSE EQ instruments.")
    
    db = SessionLocal()
    try:
        # Load all existing instruments from DB to map by key and (symbol, series, exchange)
        existing_instruments = db.query(InstrumentMaster).all()
        
        # Build lookup maps
        key_map = {}
        symbol_map = {}
        for inst in existing_instruments:
            if inst.instrument_key:
                key_map[inst.instrument_key] = inst
            symbol_map[(inst.symbol.upper(), inst.series.upper(), inst.exchange.upper())] = inst
            
        inserted = 0
        updated = 0
        ignored = 0
        
        for idx, row in df_filtered.iterrows():
            symbol = str(row['trading_symbol']).strip().upper()
            name = str(row['name']).strip()
            isin = str(row['isin']).strip()
            
            # Basic validation
            if len(isin) != 12 or not isin.isalnum():
                print(f"[INSTRUMENT_MAPPING] [WARNING] Excluding invalid instrument due to bad ISIN: {symbol} ({isin})")
                ignored += 1
                continue
                
            key = f"NSE_EQ|{isin}"
            
            # Find matching instrument by key or by symbol coordinates
            inst = key_map.get(key)
            if not inst:
                inst = symbol_map.get((symbol, 'EQ', 'NSE'))
                
            if inst:
                # Update existing record
                changed = False
                if inst.instrument_key != key:
                    inst.instrument_key = key
                    changed = True
                if inst.company_name != name:
                    inst.company_name = name
                    changed = True
                if inst.isin_code != isin:
                    inst.isin_code = isin
                    changed = True
                if inst.symbol != symbol:
                    inst.symbol = symbol
                    changed = True
                if inst.series != 'EQ':
                    inst.series = 'EQ'
                    changed = True
                if inst.exchange != 'NSE':
                    inst.exchange = 'NSE'
                    changed = True
                if not inst.is_active:
                    inst.is_active = True
                    changed = True
                if changed:
                    inst.updated_at = pd.Timestamp.utcnow()
                    updated += 1
            else:
                # Insert new record
                new_inst = InstrumentMaster(
                    symbol=symbol,
                    series='EQ',
                    exchange='NSE',
                    company_name=name,
                    isin_code=isin,
                    instrument_key=key,
                    sector='Others',
                    is_active=True
                )
                db.add(new_inst)
                inserted += 1
                # Update maps to prevent duplicates if any slip through
                key_map[key] = new_inst
                symbol_map[(symbol, 'EQ', 'NSE')] = new_inst
                
        db.commit()
        print(f"[CSV_IMPORT] Sync complete.")
        print(f"[CSV_IMPORT] Summary - Inserted: {inserted}, Updated: {updated}, Ignored/Invalid: {ignored}")
    except Exception as e:
        db.rollback()
        print(f"[CSV_IMPORT] [ERROR] Error during sync: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    sync()
