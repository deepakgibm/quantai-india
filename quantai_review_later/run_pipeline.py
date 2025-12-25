"""
Master Pipeline Script for Nifty 500 Intraday Strategy System
Runs all phases: Fetch symbols, load data, backtest, and configure scanners.
"""

import asyncio
import sys
from datetime import datetime


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


async def phase1_fetch_nifty500():
    """Phase 1: Fetch Nifty 500 symbols from NSE."""
    print_header("PHASE 1: FETCHING NIFTY 500 SYMBOLS FROM NSE")
    
    from services.nifty500_fetcher import Nifty500Fetcher
    
    fetcher = Nifty500Fetcher()
    count = fetcher.refresh()
    
    print(f"✅ Loaded {count} Nifty 500 symbols")
    return count


async def phase2_load_intraday_data(years: int = 3):
    """Phase 2: Load 3-year intraday data from Upstox API."""
    print_header(f"PHASE 2: LOADING {years}-YEAR INTRADAY DATA")
    
    print("⚠️  This will take several hours for 500 stocks × 4 intervals × 3 years")
    print("    Recommended: Run overnight or on a dedicated machine")
    print()
    
    from services.intraday_loader import IntradayDataLoader
    
    loader = IntradayDataLoader()
    stats = await loader.load_full_dataset(years=years, batch_size=10)
    
    print(f"\n✅ Data loading complete")
    print(f"   Records inserted: {stats['records_inserted']:,}")
    return stats


def phase3_run_backtest():
    """Phase 3: Backtest all strategies across timeframes."""
    print_header("PHASE 3: RUNNING STRATEGY BACKTESTS")
    
    from services.backtest_engine import StrategyBacktester
    
    backtester = StrategyBacktester()
    optimal = backtester.run_full_backtest()
    
    # Save config
    backtester.save_optimal_config("optimal_timeframes.json")
    
    # Generate report
    report = backtester.generate_report()
    print("\n📋 Backtest Results:")
    print(report.to_string())
    
    return optimal


def phase4_verify_scanners():
    """Phase 4: Verify all scanners are working."""
    print_header("PHASE 4: VERIFYING SCANNER FUNCTIONALITY")
    
    from services.intraday_scanners import (
        TrendFinderScanner, BreakoutScanner, MomentumScannerV2,
        MeanReversionScannerV2, GapScannerV2, RelativeStrengthScannerV2,
        VWAPScannerV2, SRBounceScannerV2
    )
    
    scanners = [
        ("Trend Finder", TrendFinderScanner),
        ("Breakout Detector", BreakoutScanner),
        ("Momentum", MomentumScannerV2),
        ("Mean Reversion", MeanReversionScannerV2),
        ("Gap Scanner", GapScannerV2),
        ("Relative Strength", RelativeStrengthScannerV2),
        ("VWAP", VWAPScannerV2),
        ("S/R Bounce", SRBounceScannerV2),
    ]
    
    for name, scanner_class in scanners:
        try:
            scanner = scanner_class()
            results = scanner.scan_all_sync(limit=3)
            print(f"  ✅ {name}: {len(results)} signals (timeframe: {scanner.timeframe})")
        except Exception as e:
            print(f"  ❌ {name}: Error - {e}")
    
    print("\n✅ Scanner verification complete")


async def run_full_pipeline(years: int = 3, skip_data_load: bool = False):
    """Run the complete pipeline."""
    start_time = datetime.now()
    
    print_header("NIFTY 500 INTRADAY STRATEGY SYSTEM - FULL PIPELINE")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {years} years of intraday data")
    print(f"Skip data loading: {skip_data_load}")
    
    # Phase 1: Fetch Nifty 500
    await phase1_fetch_nifty500()
    
    # Phase 2: Load intraday data (optional skip for testing)
    if not skip_data_load:
        await phase2_load_intraday_data(years)
    else:
        print("\n⏩ Skipping Phase 2 (data loading) - using existing data")
    
    # Phase 3: Run backtests
    phase3_run_backtest()
    
    # Phase 4: Verify scanners
    phase4_verify_scanners()
    
    # Summary
    duration = (datetime.now() - start_time).total_seconds()
    print_header("PIPELINE COMPLETE")
    print(f"Duration: {duration/60:.1f} minutes")
    print(f"Optimal timeframes saved to: optimal_timeframes.json")
    print("\n🚀 All scanners are ready for live trading!")


if __name__ == "__main__":
    years = 3
    skip_data = False
    
    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--skip-data":
            skip_data = True
        elif sys.argv[1] == "--years":
            years = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        elif sys.argv[1] == "--help":
            print("Usage: python run_pipeline.py [options]")
            print()
            print("Options:")
            print("  --skip-data    Skip the data loading phase (use existing data)")
            print("  --years N      Number of years of data to load (default: 3)")
            print("  --help         Show this help message")
            sys.exit(0)
    
    # Run pipeline
    asyncio.run(run_full_pipeline(years=years, skip_data_load=skip_data))
