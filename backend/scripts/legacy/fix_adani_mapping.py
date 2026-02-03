from sqlalchemy import text
from database import engine

def fix_adani():
    con = engine.connect()
    # transact = con.begin()
    try:
        # Correct ISIN for ADANIENSOL is INE441N01019
        new_key = "NSE_EQ|INE441N01019"
        con.execute(text("UPDATE stock_master SET instrument_key = :key WHERE symbol = 'ADANIENSOL'"), {"key": new_key})
        # also update 360ONE if it was messed up
        con.execute(text("UPDATE stock_master SET instrument_key = 'NSE_EQ|INE466L01038' WHERE symbol = '360ONE'"))
        
        # con.commit()
        print("Updated ADANIENSOL instrument key to NSE_EQ|INE441N01019")
    except Exception as e:
        # transact.rollback()
        print(f"Error: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    fix_adani()
