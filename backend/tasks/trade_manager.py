from celery_app import celery_app
from services.upstox_client import get_upstox_client
import asyncio
from datetime import datetime

@celery_app.task
def auto_square_off():
    asyncio.run(_auto_square_off_async())

async def _auto_square_off_async():
    print(f"[{datetime.now()}] Running Auto Square-off...")
    client = get_upstox_client()
    try:
        positions = await client.get_positions()
        for pos in positions:
            # Check if intraday and open
            qty = int(pos.get("quantity", 0))
            product = pos.get("product")
            
            if product == "I" and qty != 0:
                print(f"Squaring off {pos.get('trading_symbol')} Qty: {qty}")
                # Place counter order
                txn_type = "SELL" if qty > 0 else "BUY"
                abs_qty = abs(qty)
                
                await client.place_order(
                    instrument_token=pos.get("instrument_token"),
                    quantity=abs_qty,
                    product="I",
                    transaction_type=txn_type,
                    order_type="MARKET",
                    tag="AUTO_SQ_OFF"
                )
    except Exception as e:
        print(f"Error in auto square-off: {e}")
