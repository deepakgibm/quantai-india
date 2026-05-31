import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.upstox_client import get_upstox_client
from config import settings
from database import SessionLocal
from services.auth.token_manager import TokenManagerService

def main():
    client = get_upstox_client()
    print("Settings UPSTOX_ACCESS_TOKEN:", settings.UPSTOX_ACCESS_TOKEN[:30] + "..." if settings.UPSTOX_ACCESS_TOKEN else "None")
    
    db = SessionLocal()
    try:
        manager = TokenManagerService(db)
        db_token = manager.get_analytics_token()
        print("Database Analytics Token:", db_token[:30] + "..." if db_token else "None")
        health = manager.check_token_health()
        print("Token Health:", health)
    finally:
        db.close()
        
    print("Active client token:", client.access_token[:30] + "..." if client.access_token else "None")

if __name__ == "__main__":
    main()
