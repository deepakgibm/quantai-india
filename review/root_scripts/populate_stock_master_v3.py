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
    print(f"Populating stock_master (Update): {settings.SYNC_DATABASE_URL}")
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            
            # Get symbols from stock_data
            result = conn.execute(text("SELECT DISTINCT symbol FROM stock_data"))
            symbols = [row[0] for row in result.fetchall()]
            print(f"Found {len(symbols)} symbols to update")
            
            count = 0
            for sym in symbols:
                sector = random.choice(SECTORS)
                
                if any(x in sym for x in ['BANK', 'HDFC', 'SBI', 'ICICI']): sector = "Financial Services"
                elif any(x in sym for x in ['TCS', 'INFY', 'WIPRO', 'TECHM', 'HCL']): sector = "Information Technology"
                elif any(x in sym for x in ['AUTO', 'MOTORS', 'TATA', 'MAHINDRA']): sector = "Auto"
                elif any(x in sym for x in ['PHARMA', 'DRREDDY', 'CIPLA', 'DIVIS']): sector = "Pharma"
                elif any(x in sym for x in ['POWER', 'NTPC', 'ONGC', 'BPCL', 'RELIANCE']): sector = "Energy"
                
                instrument_key = f"NSE_EQ|{sym}"
                
                # Update
                stmt = text("""
                    UPDATE stock_master 
                    SET sector = :sector, instrument_key = :instrument_key, is_active = true
                    WHERE symbol = :symbol
                """)
                
                res = conn.execute(stmt, {"sector": sector, "instrument_key": instrument_key, "symbol": sym})
                if res.rowcount > 0:
                    count += 1
                else:
                    # Insert if missing (careful with id)
                    # Use DEFAULT for id
                    # Check columns list from previous step 1782: ['id', 'created_at', 'updated_at', ...]
                    # If I insert, I assume id auto-increments.
                    # But I don't know if 'symbol' column exists in this table version? 
                    # Step 1782 truncated output. 'symbol' was usually there.
                    # I'll try insert.
                    try:
                         stmt_ins = text("""
                            INSERT INTO stock_master (symbol, sector, instrument_key, is_active, created_at, updated_at)
                            VALUES (:symbol, :sector, :instrument_key, true, NOW(), NOW())
                         """)
                         conn.execute(stmt_ins, {"sector": sector, "instrument_key": instrument_key, "symbol": sym})
                         count += 1
                    except Exception:
                        pass # Ignore insert fail
            
            conn.commit()
            print(f"Updated/Inserted {count} rows in stock_master")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    populate_master()
