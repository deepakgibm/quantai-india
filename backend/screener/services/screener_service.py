"""
Screener Service — Main Orchestrator

Orchestrates the full screening pipeline:
1. Load all symbols from instrument_master
2. Fetch technical data from DB
3. Fetch financial data from yfinance
4. Run scoring engine for each stock
5. Rank and persist results
6. Cache in Redis/Dragonfly

Supports both full scoring runs and cached reads.
"""

import logging
import time
from datetime import date, datetime
from typing import Dict, List, Optional, Any

from sqlalchemy import text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from screener.data.technical_aggregator import TechnicalAggregator
from screener.data.financial_data_fetcher import FinancialDataFetcher
from screener.data.nse_data_fetcher import NSEDataFetcher
from screener.engine.scoring_engine import ScoringEngine
from screener.models import ScreenerStockScore, ScreenerConvictionList, ScreenerSectorAnalysis, ScreenerFinancials

logger = logging.getLogger(__name__)


class ScreenerService:
    """
    Main screener service that orchestrates the full scoring pipeline.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.tech_aggregator = TechnicalAggregator(db_session)
        self.fin_fetcher = FinancialDataFetcher()
        self.nse_fetcher = NSEDataFetcher()
        self.scoring_engine = ScoringEngine()

    async def run_full_screening(
        self,
        symbols: Optional[List[str]] = None,
        skip_financials: bool = False,
        top_n: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute full screening pipeline for all NIFTY 500 stocks.
        
        Args:
            symbols: Optional list of symbols to screen (default: all active)
            skip_financials: If True, skip yfinance fetch (use DB/cache only)
            top_n: If set, only score top N stocks
            
        Returns:
            Summary dict with results count, timing, etc.
        """
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("STARTING FULL SCREENING PIPELINE")
        logger.info("=" * 60)

        # 1. Load symbols
        all_stocks = await self.tech_aggregator.get_all_symbols()
        if symbols:
            all_stocks = [s for s in all_stocks if s["symbol"] in symbols]
        if top_n:
            all_stocks = all_stocks[:top_n]

        total = len(all_stocks)
        logger.info(f"Screening {total} stocks")

        # 2. Get market-level data (once for all stocks)
        nifty_data = await self.tech_aggregator.get_nifty_trend()
        logger.info(f"Market direction: {nifty_data.get('nifty_trend', 'unknown')}")

        sector_performance = await self.tech_aggregator.get_sector_performance()
        logger.info(f"Loaded performance for {len(sector_performance)} sectors")

        # 3. Score each stock
        scored_stocks = []
        errors = 0
        
        for i, stock_info in enumerate(all_stocks):
            symbol = stock_info["symbol"]
            instrument_id = stock_info["instrument_id"]
            sector = stock_info.get("sector", "Others")

            try:
                # 3a. Technical data (from DB — fast)
                tech_data = await self.tech_aggregator.get_technical_data(symbol, instrument_id)
                
                if not tech_data.get("cmp"):
                    logger.debug(f"[{i+1}/{total}] {symbol}: No price data, skipping")
                    continue

                # 3b. Financial data: Try DB first, check freshness, only call yfinance as a last resort
                fin_data = await self._get_financials_from_db(symbol)
                
                is_fresh = False
                if fin_data and fin_data.get("updated_at"):
                    age = datetime.now() - fin_data["updated_at"].replace(tzinfo=None)
                    if age.days < 30:
                        is_fresh = True
                
                # Fetch from yfinance only if not fresh and skip_financials is False
                if not is_fresh and not skip_financials:
                    logger.info(f"[{i+1}/{total}] {symbol}: Financials not fresh or missing in DB, fetching from yfinance...")
                    yf_data = self.fin_fetcher.fetch_financials(symbol)
                    if yf_data and yf_data.get("data_available"):
                        fin_data = yf_data
                        await self._persist_financials(symbol, fin_data)
                        logger.info(f"[{i+1}/{total}] {symbol}: Successfully fetched and cached fresh financials from yfinance")
                    else:
                        logger.warning(f"[{i+1}/{total}] {symbol}: yfinance failed ({yf_data.get('error') if yf_data else 'No data'})")
                
                if not fin_data:
                    # Fallback to empty default data
                    fin_data = {"data_available": False}

                # 3c. Holdings history (from DB if available)
                holdings_history = await self._get_holdings_history(symbol)

                # 3d. Bulk deals (from DB if available)
                bulk_deals = await self._get_bulk_deals(symbol)

                # 3e. Score the stock
                result = self.scoring_engine.score_stock(
                    symbol=symbol,
                    technical_data=tech_data,
                    financial_data=fin_data,
                    nifty_data=nifty_data,
                    sector=sector,
                    sector_performance=sector_performance,
                    holdings_history=holdings_history,
                    bulk_deals=bulk_deals,
                )

                # Add company name from instrument_master
                result["company_name"] = stock_info.get("company_name", symbol)
                
                scored_stocks.append(result)

                if (i + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"[{i+1}/{total}] Scored {len(scored_stocks)} stocks ({elapsed:.1f}s elapsed)")

            except Exception as e:
                logger.error(f"[{i+1}/{total}] {symbol}: Scoring error: {e}")
                errors += 1
                continue

        # 4. Rank all scored stocks
        ranked_stocks = self.scoring_engine.rank_stocks(scored_stocks)

        # 5. Generate conviction lists
        buy_list, avoid_list = self.scoring_engine.get_conviction_list(ranked_stocks)

        # 6. Add investment thesis and trade params
        for stock in buy_list:
            thesis = self.scoring_engine.generate_investment_thesis(stock)
            trade_params = self.scoring_engine.calculate_trade_params(stock)
            stock.update(thesis)
            stock.update(trade_params)

        # 7. Persist to database
        await self._persist_scores(ranked_stocks)
        await self._persist_conviction_list(buy_list, "BUY")
        await self._persist_conviction_list(avoid_list, "AVOID")
        await self._persist_sector_analysis(ranked_stocks, sector_performance)

        elapsed = round(time.time() - start_time, 2)
        
        summary = {
            "total_screened": total,
            "total_scored": len(scored_stocks),
            "errors": errors,
            "buy_list_count": len(buy_list),
            "avoid_list_count": len(avoid_list),
            "top_stock": ranked_stocks[0]["symbol"] if ranked_stocks else None,
            "top_score": ranked_stocks[0]["overall_score"] if ranked_stocks else None,
            "duration_seconds": elapsed,
            "score_date": date.today().isoformat(),
            "nifty_trend": nifty_data.get("nifty_trend"),
        }

        logger.info("=" * 60)
        logger.info(f"SCREENING COMPLETE: {len(scored_stocks)} stocks scored in {elapsed}s")
        top5_str = [f"{s['symbol']}({s['overall_score']})" for s in ranked_stocks[:5]]
        logger.info(f"Top 5: {top5_str}")
        logger.info(f"Buy List: {len(buy_list)} | Avoid: {len(avoid_list)}")
        logger.info("=" * 60)

        return summary

    async def get_ranked_stocks(
        self,
        score_date: Optional[str] = None,
        sector: Optional[str] = None,
        conviction: Optional[str] = None,
        min_score: float = 0,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """Get ranked stocks from the database with filters."""
        query = """
            SELECT * FROM screener_stock_score
            WHERE score_date = :score_date
        """
        params: Dict[str, Any] = {"score_date": score_date or date.today().isoformat()}

        if sector:
            query += " AND sector = :sector"
            params["sector"] = sector
        if conviction:
            query += " AND conviction_level = :conviction"
            params["conviction"] = conviction
        if min_score > 0:
            query += " AND overall_score >= :min_score"
            params["min_score"] = min_score

        query += " ORDER BY rank ASC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        result = await self.db.execute(text(query), params)
        return [dict(row._mapping) for row in result]

    async def get_conviction_list(self, list_type: str = "BUY", score_date: Optional[str] = None) -> List[Dict]:
        """Get the conviction BUY or AVOID list."""
        query = """
            SELECT * FROM screener_conviction_list
            WHERE score_date = :score_date AND list_type = :list_type
            ORDER BY rank ASC
        """
        params = {
            "score_date": score_date or date.today().isoformat(),
            "list_type": list_type,
        }
        result = await self.db.execute(text(query), params)
        return [dict(row._mapping) for row in result]

    async def get_stock_detail(self, symbol: str, score_date: Optional[str] = None) -> Optional[Dict]:
        """Get detailed scoring for a single stock."""
        query = """
            SELECT * FROM screener_stock_score
            WHERE symbol = :symbol AND score_date = :score_date
        """
        params = {"symbol": symbol, "score_date": score_date or date.today().isoformat()}
        result = await self.db.execute(text(query), params)
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None

    async def get_sector_rotation(self, score_date: Optional[str] = None) -> List[Dict]:
        """Get sector rotation analysis."""
        query = """
            SELECT * FROM screener_sector_analysis
            WHERE score_date = :score_date
            ORDER BY sector_score DESC
        """
        params = {"score_date": score_date or date.today().isoformat()}
        result = await self.db.execute(text(query), params)
        return [dict(row._mapping) for row in result]

    async def get_available_dates(self) -> List[str]:
        """Get list of dates that have scoring data."""
        result = await self.db.execute(text("""
            SELECT DISTINCT score_date FROM screener_stock_score
            ORDER BY score_date DESC
            LIMIT 30
        """))
        return [str(row[0]) for row in result]

    async def _get_financials_from_db(self, symbol: str) -> Optional[Dict]:
        """Get latest cached financials from DB."""
        result = await self.db.execute(text("""
            SELECT * FROM screener_financials
            WHERE symbol = :symbol
            ORDER BY updated_at DESC
            LIMIT 1
        """), {"symbol": symbol})
        row = result.fetchone()
        if row:
            data = dict(row._mapping)
            data["data_available"] = True
            return data
        return None

    async def _persist_financials(self, symbol: str, data: Dict):
        """Cache fetched financials to DB."""
        try:
            # Delete existing to keep only latest (or we could keep history)
            await self.db.execute(text(
                "DELETE FROM screener_financials WHERE symbol = :s"
            ), {"s": symbol})
            
            entry = ScreenerFinancials(
                symbol=symbol,
                period_type="quarterly",
                period_end=date.today(),
                updated_at=datetime.now(),
                market_cap=data.get("market_cap_cr") or data.get("market_cap"),
                pe_ratio=data.get("pe_ratio"),
                pb_ratio=data.get("pb_ratio"),
                dividend_yield=data.get("dividend_yield"),
                revenue_growth_yoy=data.get("revenue_growth_yoy"),
                profit_growth_yoy=data.get("profit_growth_yoy"),
                ebitda_margin=data.get("ebitda_margin"),
                roe=data.get("roe"),
                roce=data.get("roce"),
                debt_to_equity=data.get("debt_to_equity"),
                interest_coverage=data.get("interest_coverage"),
                operating_cash_flow=data.get("operating_cash_flow_cr") or data.get("operating_cash_flow"),
                free_cash_flow=data.get("free_cash_flow_cr") or data.get("free_cash_flow"),
                sales_cagr_3y=data.get("sales_cagr_3y"),
                profit_cagr_3y=data.get("profit_cagr_3y"),
                data_source="yfinance"
            )
            self.db.add(entry)
            await self.db.flush() # Flush instead of commit here as it's part of a loop
        except Exception as e:
            logger.warning(f"Failed to persist financials for {symbol}: {e}")

    # === Private Methods ===

    async def _get_holdings_history(self, symbol: str) -> List[Dict]:
        """Get holdings history from DB."""
        result = await self.db.execute(text("""
            SELECT * FROM screener_holdings_history
            WHERE symbol = :symbol
            ORDER BY quarter_end DESC
            LIMIT 4
        """), {"symbol": symbol})
        return [dict(row._mapping) for row in result]

    async def _get_bulk_deals(self, symbol: str) -> List[Dict]:
        """Get recent bulk deals from DB."""
        result = await self.db.execute(text("""
            SELECT * FROM screener_bulk_deals
            WHERE symbol = :symbol
            ORDER BY trade_date DESC
            LIMIT 10
        """), {"symbol": symbol})
        return [dict(row._mapping) for row in result]

    async def _persist_scores(self, ranked_stocks: List[Dict]):
        """Persist scoring results to screener_stock_score table."""
        today = date.today()
        
        # Delete today's existing scores
        await self.db.execute(text(
            "DELETE FROM screener_stock_score WHERE score_date = :d"
        ), {"d": today})
        
        for stock in ranked_stocks:
            score = ScreenerStockScore(
                symbol=stock["symbol"],
                score_date=today,
                cmp=stock.get("cmp"),
                market_cap_cr=stock.get("market_cap_cr"),
                sector=stock.get("sector"),
                promoter_score=stock["dimension_scores"].get("promoter"),
                promoter_holding=stock.get("promoter_holding"),
                promoter_pledge=stock.get("promoter_pledge"),
                institutional_score=stock["dimension_scores"].get("institutional"),
                fii_holding=stock.get("fii_holding"),
                dii_holding=stock.get("dii_holding"),
                fii_change_qoq=stock.get("fii_change_qoq"),
                dii_change_qoq=stock.get("dii_change_qoq"),
                earnings_score=stock["dimension_scores"].get("earnings"),
                revenue_growth=stock.get("revenue_growth"),
                profit_growth=stock.get("profit_growth"),
                roe_latest=stock.get("roe"),
                roce_latest=stock.get("roce"),
                debt_score=stock["dimension_scores"].get("debt"),
                debt_to_equity=stock.get("debt_to_equity"),
                interest_coverage_val=stock.get("interest_coverage"),
                order_book_score=stock["dimension_scores"].get("order_book"),
                sector_score=stock["dimension_scores"].get("sector"),
                sector_rank=stock.get("sector_rank"),
                technical_score=stock["dimension_scores"].get("technical"),
                pct_from_52w_high=stock.get("pct_from_52w_high"),
                relative_strength=stock.get("relative_strength"),
                market_score=stock["dimension_scores"].get("market"),
                overall_score=stock["overall_score"],
                rank=stock["rank"],
                conviction_level=stock["conviction_level"],
                score_breakdown=stock.get("dimension_scores"),
            )
            self.db.add(score)

        await self.db.commit()
        logger.info(f"Persisted {len(ranked_stocks)} stock scores")

    async def _persist_conviction_list(self, stocks: List[Dict], list_type: str):
        """Persist conviction list to DB."""
        today = date.today()
        
        await self.db.execute(text(
            "DELETE FROM screener_conviction_list WHERE score_date = :d AND list_type = :lt"
        ), {"d": today, "lt": list_type})

        for stock in stocks:
            entry = ScreenerConvictionList(
                symbol=stock["symbol"],
                score_date=today,
                rank=stock["rank"],
                conviction_level=stock["conviction_level"],
                list_type=list_type,
                company_name=stock.get("company_name"),
                sector=stock.get("sector"),
                cmp=stock.get("cmp"),
                market_cap_cr=stock.get("market_cap_cr"),
                promoter_holding=stock.get("promoter_holding"),
                fii_holding=stock.get("fii_holding"),
                dii_holding=stock.get("dii_holding"),
                sales_growth=stock.get("revenue_growth"),
                profit_growth=stock.get("profit_growth"),
                roe=stock.get("roe"),
                roce=stock.get("roce"),
                debt_to_equity=stock.get("debt_to_equity"),
                overall_score=stock["overall_score"],
                why_buy=stock.get("why_buy"),
                risk_factors=stock.get("risk_factors"),
                buy_zone_low=stock.get("buy_zone_low"),
                buy_zone_high=stock.get("buy_zone_high"),
                stop_loss=stock.get("stop_loss"),
                target_1y=stock.get("target_1y"),
                target_3y=stock.get("target_3y"),
            )
            self.db.add(entry)

        await self.db.commit()
        logger.info(f"Persisted {len(stocks)} conviction list entries ({list_type})")

    async def _persist_sector_analysis(self, ranked_stocks: List[Dict], sector_performance: Dict):
        """Aggregate and persist sector-level analysis."""
        today = date.today()

        await self.db.execute(text(
            "DELETE FROM screener_sector_analysis WHERE score_date = :d"
        ), {"d": today})

        # Group stocks by sector
        sector_groups: Dict[str, List[Dict]] = {}
        for stock in ranked_stocks:
            sector = stock.get("sector", "Others")
            if sector not in sector_groups:
                sector_groups[sector] = []
            sector_groups[sector].append(stock)

        for sector, stocks in sector_groups.items():
            scores = [s["overall_score"] for s in stocks]
            avg_score = sum(scores) / len(scores) if scores else 0

            # Leaders (top 3)
            sorted_stocks = sorted(stocks, key=lambda x: x["overall_score"], reverse=True)
            leaders = [
                {"symbol": s["symbol"], "score": s["overall_score"]}
                for s in sorted_stocks[:3]
            ]

            # Sector performance data
            perf = sector_performance.get(sector, {})
            momentum_1m = perf.get("avg_return_1m", 0)

            # Rotation signal
            if avg_score > 65 and momentum_1m > 3:
                rotation = "ACCUMULATE"
                outlook_6m = "BULLISH"
            elif avg_score > 55:
                rotation = "HOLD"
                outlook_6m = "NEUTRAL"
            elif avg_score > 40:
                rotation = "REDUCE"
                outlook_6m = "NEUTRAL"
            else:
                rotation = "AVOID"
                outlook_6m = "BEARISH"

            entry = ScreenerSectorAnalysis(
                sector=sector,
                score_date=today,
                sector_score=round(avg_score, 1),
                avg_stock_score=round(avg_score, 1),
                stock_count=len(stocks),
                rotation_signal=rotation,
                momentum_3m=perf.get("avg_return_3m"),
                momentum_6m=perf.get("avg_return_6m"),
                momentum_1y=perf.get("avg_return_1y"),
                leaders=leaders,
                avg_fii_holding=None,
                avg_fii_change=None,
                avg_dii_holding=None,
                outlook_6m=outlook_6m,
                outlook_2y="NEUTRAL",
                outlook_5y="BULLISH",
            )
            self.db.add(entry)

        await self.db.commit()
        logger.info(f"Persisted sector analysis for {len(sector_groups)} sectors")
