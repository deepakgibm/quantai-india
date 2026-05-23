"""
Screener Scoring ETL

Standalone script to run the full screening pipeline.
Can be executed manually or scheduled via cron/Celery.

Usage:
    python -m screener.etl.run_screener_scoring
    python -m screener.etl.run_screener_scoring --skip-financials
    python -m screener.etl.run_screener_scoring --top-n 50
    python -m screener.etl.run_screener_scoring --dry-run
"""

import sys
import os
import argparse
import logging
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("screener.etl")


def create_tables():
    """Create screener tables if they don't exist."""
    from database import sync_engine
    from screener.models import (
        ScreenerFinancials, ScreenerHoldingsHistory,
        ScreenerInsiderActivity, ScreenerBulkDeals,
        ScreenerStockScore, ScreenerConvictionList,
        ScreenerSectorAnalysis,
    )
    from database import Base

    logger.info("Creating screener tables...")
    Base.metadata.create_all(bind=sync_engine, tables=[
        ScreenerFinancials.__table__,
        ScreenerHoldingsHistory.__table__,
        ScreenerInsiderActivity.__table__,
        ScreenerBulkDeals.__table__,
        ScreenerStockScore.__table__,
        ScreenerConvictionList.__table__,
        ScreenerSectorAnalysis.__table__,
    ])
    logger.info("Tables created successfully")


async def async_run_scoring(skip_financials: bool = False, top_n: int = None, dry_run: bool = False):
    """Execute the full scoring pipeline asynchronously."""
    from database import AsyncSessionLocal
    from screener.services.screener_service import ScreenerService

    start = time.time()

    # 1. Ensure tables exist
    create_tables()

    if dry_run:
        logger.info("DRY RUN — validating configuration only")
        
        async with AsyncSessionLocal() as session:
            from screener.data.technical_aggregator import TechnicalAggregator
            agg = TechnicalAggregator(session)
            
            symbols = await agg.get_all_symbols()
            logger.info(f"Found {len(symbols)} active symbols")
            
            nifty = await agg.get_nifty_trend()
            logger.info(f"NIFTY trend: {nifty.get('nifty_trend')}")
            
            sectors = await agg.get_sector_performance()
            logger.info(f"Sector data for {len(sectors)} sectors")
            
            if symbols:
                test_symbol = symbols[0]
                tech_data = await agg.get_technical_data(test_symbol["symbol"], test_symbol["instrument_id"])
                logger.info(f"Test technical data for {test_symbol['symbol']}: CMP={tech_data.get('cmp')}")

            logger.info(f"DRY RUN complete in {time.time() - start:.1f}s")
            logger.info("✅ Configuration valid. Run without --dry-run to execute scoring.")
            return

    # 2. Execute full scoring
    logger.info("=" * 70)
    logger.info("INSTITUTIONAL TRADE SCREENER — SCORING PIPELINE")
    logger.info("=" * 70)

    async with AsyncSessionLocal() as session:
        service = ScreenerService(session)
        summary = await service.run_full_screening(
            skip_financials=skip_financials,
            top_n=top_n,
        )

    elapsed = time.time() - start
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("SCORING SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Stocks Screened:  {summary.get('total_screened', 0)}")
    logger.info(f"  Stocks Scored:    {summary.get('total_scored', 0)}")
    logger.info(f"  Errors:           {summary.get('errors', 0)}")
    logger.info(f"  BUY List:         {summary.get('buy_list_count', 0)} stocks")
    logger.info(f"  AVOID List:       {summary.get('avoid_list_count', 0)} stocks")
    logger.info(f"  Top Stock:        {summary.get('top_stock', 'N/A')} (Score: {summary.get('top_score', 'N/A')})")
    logger.info(f"  Market Direction: {summary.get('nifty_trend', 'N/A')}")
    logger.info(f"  Total Duration:   {elapsed:.1f}s")
    logger.info("=" * 70)

    # Print top 10
    from database import sync_engine
    from sqlalchemy.orm import Session
    with Session(sync_engine) as session:
        from sqlalchemy import text
        result = session.execute(text("""
            SELECT rank, symbol, sector, overall_score, conviction_level, 
                   cmp, promoter_score, institutional_score, earnings_score, 
                   technical_score, debt_score
            FROM screener_stock_score
            WHERE score_date = (SELECT MAX(score_date) FROM screener_stock_score)
            ORDER BY rank ASC
            LIMIT 10
        """))
        
        rows = result.fetchall()
        if rows:
            logger.info("")
            logger.info("TOP 10 CONVICTION STOCKS:")
            logger.info("-" * 120)
            logger.info(f"{'Rank':<5} {'Symbol':<12} {'Sector':<20} {'Score':<8} {'Conv':<12} {'CMP':<10} {'Prom':<6} {'Inst':<6} {'Earn':<6} {'Tech':<6} {'Debt':<6}")
            logger.info("-" * 120)
            for row in rows:
                logger.info(
                    f"{row[0]:<5} {row[1]:<12} {(row[2] or 'N/A'):<20} "
                    f"{row[3]:<8.1f} {row[4]:<12} {row[5] or 0:<10.2f} "
                    f"{row[6] or 0:<6.0f} {row[7] or 0:<6.0f} {row[8] or 0:<6.0f} "
                    f"{row[9] or 0:<6.0f} {row[10] or 0:<6.0f}"
                )
            logger.info("-" * 120)


def run_scoring(skip_financials: bool = False, top_n: int = None, dry_run: bool = False):
    import asyncio
    asyncio.run(async_run_scoring(skip_financials, top_n, dry_run))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trade Screener Scoring Pipeline")
    parser.add_argument("--skip-financials", action="store_true",
                       help="Skip yfinance data fetch (technical-only scoring)")
    parser.add_argument("--top-n", type=int, default=None,
                       help="Only score top N symbols (for testing)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Validate configuration without running scoring")
    
    args = parser.parse_args()
    
    run_scoring(
        skip_financials=args.skip_financials,
        top_n=args.top_n,
        dry_run=args.dry_run,
    )
