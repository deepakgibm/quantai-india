"""
Trade Screener API Router

FastAPI endpoints for the institutional-grade stock screener.
All endpoints require authentication.
"""

import logging
from datetime import date, datetime
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db
from models import User
from utils.auth import get_current_user
from utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Trade Screener"],
    dependencies=[Depends(rate_limit(30, 60, "screener"))],
)


# === Helpers ===

async def get_latest_score_date(db: AsyncSession) -> date:
    """Helper to find the most recent date with complete scoring data (>= 300 stocks).
    
    IMPORTANT: result.scalar() is a SYNCHRONOUS method on the buffered 
    CursorResult returned by 'await db.execute()'. Do NOT 'await' it.
    """
    try:
        # First, try to get the latest date with at least 300 stock scores
        result = await db.execute(text("""
            SELECT score_date FROM screener_stock_score
            GROUP BY score_date
            HAVING COUNT(*) >= 300
            ORDER BY score_date DESC
            LIMIT 1
        """))
        latest = result.scalar()
        if latest is not None:
            if isinstance(latest, str):
                return datetime.strptime(latest, "%Y-%m-%d").date()
            return latest
    except Exception as e:
        logger.warning(f"Failed to fetch latest score date with complete data: {e}")

    # Fallback to absolute max date if no date has >= 100 stocks
    try:
        result = await db.execute(text("SELECT MAX(score_date) FROM screener_stock_score"))
        latest = result.scalar()
        if latest is not None:
            if isinstance(latest, str):
                return datetime.strptime(latest, "%Y-%m-%d").date()
            return latest
    except Exception as e:
        logger.warning(f"Absolute max score date fallback failed: {e}")

    return date.today()


async def to_date(date_input: Optional[Union[str, date]], db: AsyncSession) -> date:
    """Helper to ensure we have a datetime.date object for SQL queries."""
    if not date_input:
        return await get_latest_score_date(db)
    if isinstance(date_input, date) and not isinstance(date_input, datetime):
        return date_input
    if isinstance(date_input, datetime):
        return date_input.date()
    try:
        return datetime.strptime(date_input, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return await get_latest_score_date(db)


def _serialize_date(val):
    """Convert date/datetime objects to ISO strings for JSON serialization."""
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val


def _safe_row_dict(row_mapping) -> dict:
    """Convert a SQLAlchemy RowMapping to a JSON-safe dict."""
    d = dict(row_mapping)
    for key, val in d.items():
        if isinstance(val, (date, datetime)):
            d[key] = val.isoformat()
    return d


# === Response Models ===

class StockScoreResponse(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    cmp: Optional[float] = None
    market_cap_cr: Optional[float] = None
    overall_score: float
    rank: Optional[int] = None
    conviction_level: Optional[str] = None
    promoter_score: Optional[float] = None
    institutional_score: Optional[float] = None
    earnings_score: Optional[float] = None
    debt_score: Optional[float] = None
    technical_score: Optional[float] = None
    sector_score: Optional[float] = None
    market_score: Optional[float] = None
    order_book_score: Optional[float] = None
    pct_from_52w_high: Optional[float] = None
    relative_strength: Optional[float] = None
    promoter_holding: Optional[float] = None
    fii_holding: Optional[float] = None
    dii_holding: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_growth: Optional[float] = None
    roe_latest: Optional[float] = None
    debt_to_equity: Optional[float] = None
    score_breakdown: Optional[dict] = None


class ConvictionEntry(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    rank: int
    conviction_level: str
    overall_score: float
    cmp: Optional[float] = None
    market_cap_cr: Optional[float] = None
    promoter_holding: Optional[float] = None
    fii_holding: Optional[float] = None
    dii_holding: Optional[float] = None
    sales_growth: Optional[float] = None
    profit_growth: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    why_buy: Optional[str] = None
    risk_factors: Optional[str] = None
    buy_zone_low: Optional[float] = None
    buy_zone_high: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1y: Optional[float] = None
    target_3y: Optional[float] = None


class SectorAnalysisResponse(BaseModel):
    sector: str
    sector_score: Optional[float] = None
    stock_count: Optional[int] = None
    rotation_signal: Optional[str] = None
    momentum_3m: Optional[float] = None
    momentum_1y: Optional[float] = None
    leaders: Optional[list] = None
    outlook_6m: Optional[str] = None
    avg_fii_holding: Optional[float] = None


# === Endpoints ===

@router.get("/rankings")
async def get_rankings(
    score_date: Optional[str] = None,
    sector: Optional[str] = None,
    conviction: Optional[str] = None,
    min_score: float = Query(0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get ranked stock list with filters.
    
    Supports filtering by sector, conviction level, minimum score.
    Paginated with limit/offset.
    """
    try:
        target_date = await to_date(score_date, db)
        
        query = """
            SELECT * FROM screener_stock_score
            WHERE score_date = :score_date
        """
        params: dict = {"score_date": target_date}

        if sector:
            query += " AND sector = :sector"
            params["sector"] = sector
        if conviction:
            query += " AND conviction_level = :conviction"
            params["conviction"] = conviction
        if min_score > 0:
            query += " AND overall_score >= :min_score"
            params["min_score"] = min_score

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) sub"
        count_result = await db.execute(text(count_query), params)
        total_count = count_result.scalar() or 0  # NO await

        # Get paginated results
        query += " ORDER BY rank ASC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        result = await db.execute(text(query), params)
        stocks = [_safe_row_dict(row) for row in result.mappings()]

        if stocks:
            try:
                from services.price_manager import get_price_service
                price_svc = get_price_service()
                symbols = [s["symbol"] for s in stocks]
                live_prices = await price_svc.get_prices_bulk(symbols)
                for s in stocks:
                    sym = s["symbol"].upper()
                    p_data = live_prices.get(sym)
                    if p_data:
                        price_val = p_data.get("ltp") or p_data.get("price") or 0.0
                        if price_val > 0:
                            s["cmp"] = price_val
            except Exception as le:
                logger.warning(f"Screener rankings: live price resolution failed: {le}")

        # Get available sectors for filter dropdown
        sectors_result = await db.execute(text("""
            SELECT DISTINCT sector FROM screener_stock_score
            WHERE score_date = :score_date AND sector IS NOT NULL
            ORDER BY sector
        """), {"score_date": target_date})
        available_sectors = [row[0] for row in sectors_result.all()]  # NO await

        return {
            "status": "success",
            "data": stocks,
            "total_count": total_count,
            "page_size": limit,
            "offset": offset,
            "score_date": target_date.isoformat(),
            "filters": {
                "available_sectors": available_sectors,
                "available_convictions": ["EXTREME", "VERY_HIGH", "HIGH", "MODERATE", "AVOID"],
            }
        }

    except Exception as e:
        logger.error(f"Rankings API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conviction-list")
async def get_conviction_list(
    list_type: str = Query("BUY", regex="^(BUY|AVOID)$"),
    score_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the high-conviction BUY or AVOID list."""
    try:
        target_date = await to_date(score_date, db)

        result = await db.execute(text("""
            SELECT * FROM screener_conviction_list
            WHERE score_date = :score_date AND list_type = :list_type
            ORDER BY rank ASC
        """), {"score_date": target_date, "list_type": list_type})

        stocks = [_safe_row_dict(row) for row in result.mappings()]

        if stocks:
            try:
                from services.price_manager import get_price_service
                price_svc = get_price_service()
                symbols = [s["symbol"] for s in stocks]
                live_prices = await price_svc.get_prices_bulk(symbols)
                for s in stocks:
                    sym = s["symbol"].upper()
                    p_data = live_prices.get(sym)
                    if p_data:
                        price_val = p_data.get("ltp") or p_data.get("price") or 0.0
                        if price_val > 0:
                            s["cmp"] = price_val
            except Exception as le:
                logger.warning(f"Screener conviction list: live price resolution failed: {le}")

        # Score distribution
        score_dist = {"extreme": 0, "very_high": 0, "high": 0, "moderate": 0}
        for s in stocks:
            level = (s.get("conviction_level") or "").lower()
            if level in score_dist:
                score_dist[level] += 1

        return {
            "status": "success",
            "list_type": list_type,
            "data": stocks,
            "count": len(stocks),
            "score_date": target_date.isoformat(),
            "distribution": score_dist,
        }

    except Exception as e:
        logger.error(f"Conviction list API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/avoid-list")
async def get_avoid_list(
    score_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get stocks to avoid."""
    try:
        target_date = await to_date(score_date, db)

        result = await db.execute(text("""
            SELECT * FROM screener_stock_score
            WHERE score_date = :score_date AND conviction_level = 'AVOID'
            ORDER BY overall_score ASC
            LIMIT 20
        """), {"score_date": target_date})

        stocks = [_safe_row_dict(row) for row in result.mappings()]

        if stocks:
            try:
                from services.price_manager import get_price_service
                price_svc = get_price_service()
                symbols = [s["symbol"] for s in stocks]
                live_prices = await price_svc.get_prices_bulk(symbols)
                for s in stocks:
                    sym = s["symbol"].upper()
                    p_data = live_prices.get(sym)
                    if p_data:
                        price_val = p_data.get("ltp") or p_data.get("price") or 0.0
                        if price_val > 0:
                            s["cmp"] = price_val
            except Exception as le:
                logger.warning(f"Screener avoid list: live price resolution failed: {le}")

        return {
            "status": "success",
            "data": stocks,
            "count": len(stocks),
            "score_date": target_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"Avoid list API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{symbol}")
async def get_stock_detail(
    symbol: str,
    score_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed scoring analysis for a single stock."""
    try:
        target_date = await to_date(score_date, db)

        # Get score data
        result = await db.execute(text("""
            SELECT * FROM screener_stock_score
            WHERE symbol = :symbol AND score_date = :score_date
        """), {"symbol": symbol.upper(), "score_date": target_date})

        row = result.fetchone()  # NO await
        if not row:
            raise HTTPException(status_code=404, detail=f"No scoring data for {symbol} on {target_date}")

        stock_data = _safe_row_dict(row._mapping)

        try:
            from services.price_manager import get_price_service
            price_svc = get_price_service()
            p_data = await price_svc.get_price(symbol)
            if p_data:
                price_val = p_data.get("ltp") or p_data.get("price") or 0.0
                if price_val > 0:
                    stock_data["cmp"] = price_val
        except Exception as le:
            logger.warning(f"Screener stock detail: live price resolution failed: {le}")

        # Get conviction entry if exists
        conv_result = await db.execute(text("""
            SELECT why_buy, risk_factors, buy_zone_low, buy_zone_high,
                   stop_loss, target_1y, target_3y
            FROM screener_conviction_list
            WHERE symbol = :symbol AND score_date = :score_date
            LIMIT 1
        """), {"symbol": symbol.upper(), "score_date": target_date})

        conv_row = conv_result.fetchone()  # NO await
        if conv_row:
            stock_data.update(_safe_row_dict(conv_row._mapping))

        # Get historical scores for this stock
        history_result = await db.execute(text("""
            SELECT score_date, overall_score, conviction_level
            FROM screener_stock_score
            WHERE symbol = :symbol
            ORDER BY score_date DESC
            LIMIT 30
        """), {"symbol": symbol.upper()})
        
        stock_data["score_history"] = [_safe_row_dict(row) for row in history_result.mappings()]

        return {
            "status": "success",
            "data": stock_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stock detail API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/composite-score/{symbol}")
async def get_composite_score(
    symbol: str, 
    current_user: User = Depends(get_current_user)
):
    """
    Returns the real-time V2 composite score for a stock, factoring in
    DuckDB technicals alongside PG Fundamentals and Block deal flows.
    Fully cached via Redis for screener speed.
    """
    try:
        from services.dragonfly_client import get_cache
        cache = get_cache()
        if cache.is_available():
            cached_score = cache.get(f"screener:composite:{symbol.upper()}")
            if cached_score:
                return {"status": "success", "source": "cache", "data": cached_score}
                
        # If not in cache, actively trigger calculation
        from core.scanner.composite_scorer import scoring_engine
        result = scoring_engine.score_symbol(symbol.upper())
        return {"status": "success", "source": "computed", "data": result}
    except Exception as e:
        logger.error(f"Composite score API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sector-rotation")
async def get_sector_rotation(
    score_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get sector rotation analysis and insights."""
    try:
        target_date = await to_date(score_date, db)

        result = await db.execute(text("""
            SELECT * FROM screener_sector_analysis
            WHERE score_date = :score_date
            ORDER BY sector_score DESC
        """), {"score_date": target_date})

        sectors = [_safe_row_dict(row) for row in result.mappings()]

        # Aggregate insights
        accumulate = [s for s in sectors if s.get("rotation_signal") == "ACCUMULATE"]
        avoid = [s for s in sectors if s.get("rotation_signal") == "AVOID"]

        return {
            "status": "success",
            "data": sectors,
            "count": len(sectors),
            "score_date": target_date.isoformat(),
            "insights": {
                "sectors_to_accumulate": [s["sector"] for s in accumulate],
                "sectors_to_avoid": [s["sector"] for s in avoid],
                "top_sector": sectors[0]["sector"] if sectors else None,
            }
        }

    except Exception as e:
        logger.error(f"Sector rotation API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios")
async def get_model_portfolios(
    score_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get model portfolio recommendations."""
    try:
        target_date = await to_date(score_date, db)

        # Conservative: high debt score + high promoter score + high overall
        conservative_result = await db.execute(text("""
            SELECT s.*, c.why_buy, c.risk_factors, c.buy_zone_low, c.buy_zone_high,
                   c.stop_loss, c.target_1y, c.target_3y
            FROM screener_stock_score s
            LEFT JOIN screener_conviction_list c 
                ON s.symbol = c.symbol AND s.score_date = c.score_date AND c.list_type = 'BUY'
            WHERE s.score_date = :score_date
              AND s.overall_score >= 60
              AND COALESCE(s.debt_score, 50) >= 55
              AND COALESCE(s.promoter_score, 50) >= 50
            ORDER BY s.overall_score DESC
            LIMIT 12
        """), {"score_date": target_date})
        conservative = [_safe_row_dict(row) for row in conservative_result.mappings()]

        # Growth: high earnings + high revenue growth
        growth_result = await db.execute(text("""
            SELECT s.*, c.why_buy, c.risk_factors, c.buy_zone_low, c.buy_zone_high,
                   c.stop_loss, c.target_1y, c.target_3y
            FROM screener_stock_score s
            LEFT JOIN screener_conviction_list c 
                ON s.symbol = c.symbol AND s.score_date = c.score_date AND c.list_type = 'BUY'
            WHERE s.score_date = :score_date
              AND s.overall_score >= 55
              AND COALESCE(s.earnings_score, 50) >= 50
            ORDER BY s.earnings_score DESC NULLS LAST
            LIMIT 15
        """), {"score_date": target_date})
        growth = [_safe_row_dict(row) for row in growth_result.mappings()]

        # Swing: high technical score
        swing_result = await db.execute(text("""
            SELECT s.*, c.why_buy, c.risk_factors, c.buy_zone_low, c.buy_zone_high,
                   c.stop_loss, c.target_1y, c.target_3y
            FROM screener_stock_score s
            LEFT JOIN screener_conviction_list c 
                ON s.symbol = c.symbol AND s.score_date = c.score_date AND c.list_type = 'BUY'
            WHERE s.score_date = :score_date
              AND COALESCE(s.technical_score, 0) >= 55
              AND COALESCE(s.pct_from_52w_high, -100) >= -15
            ORDER BY s.technical_score DESC NULLS LAST
            LIMIT 8
        """), {"score_date": target_date})
        swing = [_safe_row_dict(row) for row in swing_result.mappings()]

        return {
            "status": "success",
            "score_date": target_date.isoformat(),
            "portfolios": {
                "conservative": {
                    "name": "Conservative Value",
                    "description": "Low debt, strong promoters, high conviction — ideal for 3-5 year holding",
                    "stocks": conservative,
                    "count": len(conservative),
                },
                "growth": {
                    "name": "Aggressive Growth",
                    "description": "High earnings growth, sector leaders — ideal for 1-3 year holding",
                    "stocks": growth,
                    "count": len(growth),
                },
                "swing": {
                    "name": "Swing Trading",
                    "description": "Technical breakouts, strong momentum — ideal for 1-6 month trades",
                    "stocks": swing,
                    "count": len(swing),
                },
            }
        }

    except Exception as e:
        logger.error(f"Portfolios API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def trigger_screening(
    skip_financials: bool = Query(False),
    top_n: Optional[int] = Query(None, ge=1, le=500),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger a full screening run in the background.
    
    Returns the Task ID for tracking.
    """
    try:
        from tasks.institutional_tasks import run_screener_scoring
        task = run_screener_scoring.delay(
            skip_financials=skip_financials,
            top_n=top_n
        )
        return {
            "status": "accepted",
            "message": "Screening triggered in background",
            "task_id": task.id
        }
    except Exception as e:
        logger.error(f"Screening trigger error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_screener_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of the screener - last run date, stock counts, etc."""
    try:
        target_date = await get_latest_score_date(db)

        # Get stock count and sector count for this specific target date
        date_result = await db.execute(text("""
            SELECT COUNT(DISTINCT symbol) as stock_count,
                   COUNT(DISTINCT sector) as sector_count
            FROM screener_stock_score
            WHERE score_date = :score_date
        """), {"score_date": target_date})
        date_row = date_result.fetchone()  # NO await

        # Conviction distribution for this specific target date
        dist_result = await db.execute(text("""
            SELECT conviction_level, COUNT(*) as cnt
            FROM screener_stock_score
            WHERE score_date = :score_date
            GROUP BY conviction_level
        """), {"score_date": target_date})
        distribution = {row[0]: row[1] for row in dist_result.all()}  # NO await

        return {
            "status": "success",
            "latest_score_date": target_date.isoformat(),
            "total_stocks_scored": date_row.stock_count if date_row else 0,
            "sector_count": date_row.sector_count if date_row else 0,
            "conviction_distribution": distribution,
        }

    except Exception as e:
        logger.error(f"Status API error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
