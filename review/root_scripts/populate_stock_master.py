import os
import sys
import random
from sqlalchemy import create_engine, text

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from config import settings

SECTORS = [
    "Financial Services", "Information Technology", "Auto", "Pharma", 
    "FMCG", "Energy", "Metals", "Consumer Durables", "Telecommunication"
]

def populate_master():
    print(f"Populating stock_master: {settings.SYNC_DATABASE_URL}")
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            # Clear existing? Or update?
            # Better to clear if it's junk.
            conn.execute(text("DELETE FROM stock_master"))
            
            # Get symbols from stock_data
            result = conn.execute(text("SELECT DISTINCT symbol FROM stock_data"))
            symbols = [row[0] for row in result.fetchall()]
            print(f"Found {len(symbols)} symbols in stock_data")
            
            # Map sectors logic (Simple keyword based or random)
            data_to_insert = []
            for sym in symbols:
                sector = random.choice(SECTORS)
                
                # Heuristic mapping for better demo
                if any(x in sym for x in ['BANK', 'HDFC', 'SBI', 'ICICI']): sector = "Financial Services"
                elif any(x in sym for x in ['TCS', 'INFY', 'WIPRO', 'TECHM', 'HCL']): sector = "Information Technology"
                elif any(x in sym for x in ['AUTO', 'MOTORS', 'TATA', 'MAHINDRA']): sector = "Auto"
                elif any(x in sym for x in ['PHARMA', 'DRREDDY', 'CIPLA', 'DIVIS']): sector = "Pharma"
                elif any(x in sym for x in ['POWER', 'NTPC', 'ONGC', 'BPCL', 'RELIANCE']): sector = "Energy"
                
                # instrument_key: NSE_EQ|{symbol}
                instrument_key = f"NSE_EQ|{sym}"
                
                data_to_insert.append({
                    "symbol": sym,
                    "sector": sector,
                    "instrument_key": instrument_key,
                    "is_active": True
                })
            
            # Bulk Insert
            if data_to_insert:
                stmt = text("""
                    INSERT INTO stock_master (symbol, sector, instrument_key, is_active)
                    VALUES (:symbol, :sector, :instrument_key, :is_active)
                """)
                for item in data_to_insert:
                     conn.execute(stmt, item)
                conn.commit()
                print(f"Inserted {len(data_to_insert)} rows into stock_master")
            else:
                print("No data to insert")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    populate_master()
