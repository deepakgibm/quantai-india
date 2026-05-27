import json
import redis
from datetime import datetime, timedelta

def get_upcoming_thursdays(count=5):
    d = datetime.now()
    thursdays = []
    while d.weekday() != 3:
        d += timedelta(days=1)
    for _ in range(count):
        thursdays.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=7)
    return thursdays

def populate_mock():
    # Connect to local Dragonfly/Redis (mapped to port 6379)
    for db in [0, 1]:
        r = redis.Redis(host='localhost', port=6379, db=db, decode_responses=True)
        try:
            r.ping()
            print(f"Connected to Dragonfly/Redis DB {db} successfully.")
        except Exception as e:
            print(f"Failed to connect to Redis DB {db}: {e}")
            continue

        thursdays = get_upcoming_thursdays()
        next_expiry = thursdays[0]

        # 1. Populate RELIANCE
        reliance_strikes = []
        base_strike = 2400
        for i in range(-5, 6):
            strike = base_strike + i * 20
            c_vol = 5000 + abs(i) * 100
            p_vol = 4500 + abs(i) * 120
            c_ltp = max(1.0, 100 - i * 15)
            p_ltp = max(1.0, 5 + i * 12)
            c_prem = c_vol * c_ltp
            p_prem = p_vol * p_ltp
            reliance_strikes.append({
                "strike_price": float(strike),
                "call": {
                    "oi": 15000 - i * 1000,
                    "oi_change": 1200 + i * 100,
                    "volume": c_vol,
                    "ltp": c_ltp,
                    "bid": c_ltp - 0.1,
                    "ask": c_ltp + 0.1,
                    "premium": round(c_prem, 2),
                    "iv": 18.5
                },
                "put": {
                    "oi": 12000 + i * 1000,
                    "oi_change": 900 - i * 80,
                    "volume": p_vol,
                    "ltp": p_ltp,
                    "bid": p_ltp - 0.1,
                    "ask": p_ltp + 0.1,
                    "premium": round(p_prem, 2),
                    "iv": 19.2
                }
            })

        reliance_blocks = [
            {
                "strike_price": 2400.0,
                "type": "CE",
                "ltp": 50.0,
                "volume": 25000,
                "premium": 1250000.0,
                "oi": 45000
            },
            {
                "strike_price": 2380.0,
                "type": "PE",
                "ltp": 25.0,
                "volume": 50000,
                "premium": 1250000.0,
                "oi": 52000
            }
        ]

        reliance_data = {
            "status": "success",
            "symbol": "RELIANCE",
            "expiry": next_expiry,
            "total_call_oi": 150000,
            "total_put_oi": 120000,
            "total_call_volume": 110000,
            "total_put_volume": 105000,
            "total_call_premium": 18500000.0,
            "total_put_premium": 14200000.0,
            "net_flow": 4300000.0,
            "buy_sell_ratio": 1.3,
            "pcr_oi": 0.8,
            "pcr_volume": 0.95,
            "sentiment": "Bullish",
            "strikes": reliance_strikes,
            "block_deals": reliance_blocks,
            "is_static": True,
            "market_closed": True,
            "api_failed": False
        }

        reliance_expiries = {
            "status": "success",
            "symbol": "RELIANCE",
            "expiries": thursdays
        }

        r.set("option_expiries_snapshot:RELIANCE", json.dumps(reliance_expiries))
        r.set("option_flow_snapshot:RELIANCE:nearest:all", json.dumps(reliance_data))
        r.set(f"option_flow_snapshot:RELIANCE:{next_expiry}:all", json.dumps(reliance_data))
        print(f"RELIANCE snapshot populated in DB {db}.")

        # 2. Populate NIFTY
        nifty_strikes = []
        nifty_base = 22000
        for i in range(-5, 6):
            strike = nifty_base + i * 50
            c_vol = 25000 + abs(i) * 500
            p_vol = 22000 + abs(i) * 600
            c_ltp = max(5.0, 250 - i * 35)
            p_ltp = max(5.0, 15 + i * 28)
            c_prem = c_vol * c_ltp
            p_prem = p_vol * p_ltp
            nifty_strikes.append({
                "strike_price": float(strike),
                "call": {
                    "oi": 85000 - i * 4000,
                    "oi_change": 6500 + i * 300,
                    "volume": c_vol,
                    "ltp": c_ltp,
                    "bid": c_ltp - 0.5,
                    "ask": c_ltp + 0.5,
                    "premium": round(c_prem, 2),
                    "iv": 14.2
                },
                "put": {
                    "oi": 78000 + i * 5000,
                    "oi_change": 5800 - i * 400,
                    "volume": p_vol,
                    "ltp": p_ltp,
                    "bid": p_ltp - 0.5,
                    "ask": p_ltp + 0.5,
                    "premium": round(p_prem, 2),
                    "iv": 15.0
                }
            })

        nifty_blocks = [
            {
                "strike_price": 22000.0,
                "type": "CE",
                "ltp": 125.0,
                "volume": 80000,
                "premium": 10000000.0,
                "oi": 150000
            },
            {
                "strike_price": 21900.0,
                "type": "PE",
                "ltp": 60.0,
                "volume": 75000,
                "premium": 4500000.0,
                "oi": 125000
            }
        ]

        nifty_data = {
            "status": "success",
            "symbol": "NIFTY",
            "expiry": next_expiry,
            "total_call_oi": 850000,
            "total_put_oi": 780000,
            "total_call_volume": 650000,
            "total_put_volume": 600000,
            "total_call_premium": 82000000.0,
            "total_put_premium": 68000000.0,
            "net_flow": 14000000.0,
            "buy_sell_ratio": 1.2,
            "pcr_oi": 0.92,
            "pcr_volume": 0.92,
            "sentiment": "Neutral",
            "strikes": nifty_strikes,
            "block_deals": nifty_blocks,
            "is_static": True,
            "market_closed": True,
            "api_failed": False
        }

        nifty_expiries = {
            "status": "success",
            "symbol": "NIFTY",
            "expiries": thursdays
        }

        r.set("option_expiries_snapshot:NIFTY", json.dumps(nifty_expiries))
        r.set("option_flow_snapshot:NIFTY:nearest:all", json.dumps(nifty_data))
        r.set(f"option_flow_snapshot:NIFTY:{next_expiry}:all", json.dumps(nifty_data))
        print(f"NIFTY snapshot populated in DB {db}.")

if __name__ == "__main__":
    populate_mock()
