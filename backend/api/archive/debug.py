"""
Debug Router - Internal diagnostics endpoints
"""

from fastapi import APIRouter
from services.live_price_enricher import get_price_source_status, get_live_ltp, get_ltp_bulk

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/price-status")
async def get_price_status():
    """
    Get current price source status for debugging.
    Returns WS cache state, market status, and configuration info.
    """
    return get_price_source_status()


@router.get("/test-ltp/{symbol}")
async def test_single_ltp(symbol: str):
    """
    Test LTP fetch for a single symbol with full source metadata.
    """
    result = await get_live_ltp(symbol)
    return result


@router.post("/test-ltp-bulk")
async def test_bulk_ltp(symbols: list[str]):
    """
    Test bulk LTP fetch with source metadata.
    """
    result = await get_ltp_bulk(symbols)
    return result
