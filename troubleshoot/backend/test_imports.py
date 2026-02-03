try:
    print("Testing imports...")
    from services.top_movers_service import NIFTY_100_SYMBOLS
    print(f"NIFTY_100_SYMBOLS loaded: {len(NIFTY_100_SYMBOLS)}")
    from database import AsyncSessionLocal
    print("database.AsyncSessionLocal loaded")
    from services.hp_scanner_service import get_hp_scanner_service
    print("HPScannerService loaded")
    import asyncio
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
