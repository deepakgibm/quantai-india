import sys
import os
import time
import logging

# Add backend to path
sys.path.append("/app")

from database import SessionLocal
from screener.services.screener_service import ScreenerService

logging.basicConfig(level=logging.INFO)

def run_test():
    session = SessionLocal()
    try:
        service = ScreenerService(session)
        symbols = ["BHEL", "RELIANCE", "TCS"]
        print(f"Running screening for {symbols}...")
        summary = service.run_full_screening(symbols=symbols)
        print("Summary:", summary)
    finally:
        session.close()

if __name__ == "__main__":
    run_test()
