from datetime import datetime
import os

def is_market_open():
    now = datetime.now()
    print(f"Current Time: {now}")
    if now.weekday() >= 5: 
        print("Weekend - Closed")
        return False
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    print(f"Market Range: {start} to {end}")
    result = start <= now <= end
    print(f"Is Market Open? {result}")
    return result

if __name__ == "__main__":
    is_market_open()
