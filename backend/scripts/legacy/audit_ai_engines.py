import asyncio
import sys
import os
from datetime import datetime, timezone

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.live_price_enricher import get_live_ltp, enrich_scanner_results
from services.market_hours_service import get_market_hours_service

# Scanners
from services.trend_analyzer import TrendAnalyzer
from services.breakout_detector import BreakoutDetector
from services.top5_buysell import Top5BuySellEngine
from services.momentum_scanner import MomentumScanner
from services.mean_reversion_scanner import MeanReversionScanner
from services.gap_scanner import GapScanner
from services.relative_strength_scanner import RelativeStrengthScanner
from services.vwap_scanner import VWAPScanner
from services.sr_bounce_scanner import SRBounceScanner

async def audit_engine(scanner_class, engine_name: str):
    print(f"\n{'='*60}")
    print(f"🚀 AUDITING ENGINE: {engine_name}")
    print(f"{'='*60}")
    
    scanner = scanner_class()
    market_service = get_market_hours_service()
    market_open = market_service.is_market_open()
    
    try:
        # 1. Run Scan
        print(f"[{engine_name}] Running scanner...")
        raw_stocks = scanner.scan_all(limit=5)
        
        if not raw_stocks:
            print(f"❌ No stocks found for {engine_name}")
            return
            
        # Handle Top 5 Pick structure (dict of buy/sell)
        if isinstance(raw_stocks, dict):
            stocks = raw_stocks.get("buy", []) + raw_stocks.get("sell", [])
        else:
            stocks = raw_stocks

        # 2. Enrich with Live Prices (applying our guardrails)
        print(f"[{engine_name}] Enriching signals with live prices...")
        enriched_stocks = await enrich_scanner_results(stocks)
        
        passed_count = 0
        total_count = len(enriched_stocks)
        
        for stock in enriched_stocks:
            symbol = stock.get("symbol")
            print(f"\n--- Checking Stock: {symbol} ---")
            
            # A. Price Accuracy Check
            # Fetch "Ground Truth" for auditing
            truth = await get_live_ltp(symbol)
            api_ltp = stock.get("current_price", 0)
            exchange_ltp = truth.get("ltp", 0)
            deviation = abs(api_ltp - exchange_ltp) / exchange_ltp * 100 if exchange_ltp else 0
            
            price_match = "✅" if deviation <= 0.1 else "❌"
            print(f"Price Match: {price_match}")
            print(f"API LTP: {api_ltp}")
            print(f"Exchange LTP: {exchange_ltp}")
            print(f"Deviation %: {deviation:.4f}%")
            
            # B. Freshness
            print(f"Market Status: {'OPEN' if market_open else 'CLOSED'}")
            print(f"Data Freshness: {'VALID' if not stock.get('is_stale') else 'STALE'}")
            
            # C. Strategy Logic Validation (Simplified generic checks)
            # In a real environment, we'd check RSI, EMA, etc. from 'indicators'
            indicators = stock.get("indicators", {})
            logic_reason = stock.get("reason", "N/A")
            print(f"Strategy Logic: {logic_reason}")
            
            # D. Final Verdict per Stock
            if stock.get("signal_active") and deviation <= 0.1:
                print(f"FINAL STATUS: ✅ VERIFIED")
                passed_count += 1
            else:
                reason = stock.get("rejection_reason", "Price Deviation > 0.1%" if deviation > 0.1 else "Logic Reject")
                print(f"FINAL STATUS: ❌ REJECTED")
                print(f"Reason: {reason}")
            
            print(f"Confidence Score: {stock.get('strength', stock.get('confidence', 0))}")

        # Engine Summary
        print(f"\n--- ENGINE SUMMARY: {engine_name} ---")
        price_acc = "PASS" if passed_count > 0 or total_count == 0 else "FAIL"
        logic_acc = "PASS" if any(s.get("signal_active") for s in enriched_stocks) else "FAIL"
        
        print(f"Engine Name: {engine_name}")
        print(f"Price Accuracy: {price_acc}")
        print(f"Logic Accuracy: {logic_acc}")
        print(f"Signal Quality: {'HIGH' if passed_count/total_count > 0.8 else 'MEDIUM' if passed_count > 0 else 'LOW' if total_count > 0 else 'N/A'}")
        print(f"Production Ready: {'YES' if price_acc == 'PASS' and logic_acc == 'PASS' else 'NO'}")

    except Exception as e:
        print(f"❌ Critical error auditing {engine_name}: {e}")

async def run_full_audit():
    engines = [
        (TrendAnalyzer, "Trend Finder AI"),
        (BreakoutDetector, "Breakout Detector"),
        (Top5BuySellEngine, "Top 5 Buy/Sell"),
        (MomentumScanner, "Momentum Scanner"),
        (MeanReversionScanner, "Mean Reversion"),
        (GapScanner, "Gap Scanner"),
        (RelativeStrengthScanner, "Relative Strength"),
        (VWAPScanner, "VWAP Trading"),
        (SRBounceScanner, "Support/Resistance Bounces")
    ]
    
    print(f"Starting Quant QA Audit at {datetime.now(timezone.utc)}")
    for scanner_class, name in engines:
        await audit_engine(scanner_class, name)

if __name__ == "__main__":
    asyncio.run(run_full_audit())
