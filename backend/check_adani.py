from sqlalchemy import text
from database import engine
import json

def check_adani():
    con = engine.connect()
    try:
        # Check stock_master
        res = con.execute(text("SELECT symbol, instrument_key FROM stock_master WHERE symbol = 'ADANIENSOL'"))
        row = res.fetchone()
        print(f"Stock Master ADANIENSOL: {row}")
        
        # Check stock_candles
        res = con.execute(text("SELECT close, timestamp FROM stock_candles WHERE symbol = 'ADANIENSOL' OR instrument_key = (SELECT instrument_key FROM stock_master WHERE symbol = 'ADANIENSOL') ORDER BY timestamp DESC LIMIT 5"))
        rows = res.fetchall()
        print(f"Stock Candles ADANIENSOL: {[ (r[0], str(r[1])) for r in rows ]}")
        
    finally:
        con.close()

if __name__ == "__main__":
    check_adani()
