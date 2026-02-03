import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.live_price_enricher import enrich_scanner_results
from utils.trade_logic import validate_directional_consistency, calculate_rr_ratio

async def test_enrichment_logic():
    print("--- Testing AI Trading Signal Guardrails ---")
    
    # 1. Test Mock Signals
    mock_results = [
        {
            "symbol": "VALID_LONG",
            "signal": "BUY",
            "atr": 10.0,
            "breakout_level": 1000.0,
            "current_price": 1005.0
        },
        {
            "symbol": "INVALID_RR",
            "signal": "BUY",
            "atr": 1.0, # Very small ATR -> tight levels -> potentially low RR if fixed levels were used
            "breakout_level": 1000.0,
            "current_price": 1005.0
        },
        {
            "symbol": "INVALID_DIRECTION",
            "signal": "BUY",
            "atr": 10.0,
            "target_price": 900.0, # Target below price for BUY
            "stop_loss": 1100.0,   # SL above price for BUY
            "current_price": 1000.0
        }
    ]
    
    print("\n[Case 1] Running enrichment on mock signals...")
    # Mocking get_ltp_bulk behavior inside enrich_scanner_results
    # Since we can't easily mock the network/orchestrator here without more setup, 
    # we'll rely on the fact that enriched_results uses current_price if live_price is missing.
    
    enriched = await enrich_scanner_results(mock_results)
    
    for res in enriched:
        print(f"\nSymbol: {res['symbol']}")
        print(f"  Signal: {res.get('signal')} | Active: {res.get('signal_active')}")
        print(f"  Price: {res.get('current_price')} | Entry: {res.get('entry_price')} | Target: {res.get('target_price')} | SL: {res.get('stop_loss')}")
        print(f"  R:R: {res.get('risk_reward')} | Method: {res.get('level_method')}")
        if not res.get("signal_active"):
            print(f"  REJECTED: {res.get('rejection_reason')}")

    # 2. Manual Logic Tests
    print("\n[Case 2] Manual Directional Tests")
    
    cases = [
        (True, 100, 105, 110, 95, "Valid Long"),
        (True, 100, 105, 90, 95, "Invalid Long (Target < Entry)"),
        (False, 100, 95, 90, 105, "Valid Short"),
        (False, 100, 95, 110, 90, "Invalid Short (Target > Entry)")
    ]
    
    for is_bullish, price, entry, target, sl, desc in cases:
        valid, msg = validate_directional_consistency(is_bullish, price, entry, target, sl)
        print(f"{desc}: {'✅' if valid else '❌'} {msg}")

if __name__ == "__main__":
    asyncio.run(test_enrichment_logic())
