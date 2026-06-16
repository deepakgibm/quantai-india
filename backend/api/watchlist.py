import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from utils.auth import get_current_user
from schemas import (
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistPerformance,
    WatchlistAnalytics
)
from services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Watchlist"])

@router.get("", response_model=List[WatchlistItemResponse])
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve user's watchlist with updated live stock quotes.
    """
    try:
        items = await WatchlistService.get_watchlist(db, current_user.id)
        
        # Format response data to match schema (calculate days_tracked and status dynamically)
        response_items = []
        for item in items:
            days = WatchlistService.get_days_tracked(item.added_at)
            status_lbl = WatchlistService.get_status_label(item.change_percent or 0.0)
            
            response_items.append(
                WatchlistItemResponse(
                    id=item.id,
                    user_id=item.user_id,
                    symbol=item.symbol,
                    company_name=item.company_name,
                    exchange=item.exchange,
                    added_at=item.added_at,
                    watchlist_price=item.watchlist_price,
                    current_price=item.current_price,
                    change_percent=item.change_percent,
                    change_amount=item.change_amount,
                    last_updated=item.last_updated,
                    days_tracked=days,
                    status=status_lbl
                )
            )
        return response_items
    except Exception as e:
        logger.error(f"Error in get_watchlist API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch watchlist: {str(e)}"
        )

@router.post("", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    item_in: WatchlistItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a stock symbol to the user's watchlist.
    """
    try:
        db_item = await WatchlistService.add_to_watchlist(db, current_user.id, item_in)
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Symbol {item_in.symbol} already in watchlist or invalid instrument."
            )
            
        days = WatchlistService.get_days_tracked(db_item.added_at)
        status_lbl = WatchlistService.get_status_label(db_item.change_percent or 0.0)
        
        return WatchlistItemResponse(
            id=db_item.id,
            user_id=db_item.user_id,
            symbol=db_item.symbol,
            company_name=db_item.company_name,
            exchange=db_item.exchange,
            added_at=db_item.added_at,
            watchlist_price=db_item.watchlist_price,
            current_price=db_item.current_price,
            change_percent=db_item.change_percent,
            change_amount=db_item.change_amount,
            last_updated=db_item.last_updated,
            days_tracked=days,
            status=status_lbl
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in add_to_watchlist API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add symbol to watchlist: {str(e)}"
        )

@router.delete("/{symbol}")
async def remove_from_watchlist(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a stock symbol from the user's watchlist.
    """
    try:
        success = await WatchlistService.remove_from_watchlist(db, current_user.id, symbol)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Symbol {symbol} not found in your watchlist"
            )
        return {"status": "success", "message": f"Symbol {symbol.upper()} removed from watchlist"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in remove_from_watchlist API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove symbol: {str(e)}"
        )

@router.get("/performance", response_model=WatchlistPerformance)
async def get_watchlist_performance(
    virtual_investment: float = Query(10000.0, alias="virtualInvestment", gt=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve virtual P&L performance for the user's watchlist.
    """
    try:
        perf = await WatchlistService.get_watchlist_performance(db, current_user.id, virtual_investment)
        return WatchlistPerformance(
            total_value=perf["total_value"],
            total_pnl=perf["total_pnl"],
            pnl_percent=perf["pnl_percent"],
            total_invested=perf["total_invested"],
            accuracy_percent=perf["accuracy_percent"]
        )
    except Exception as e:
        logger.error(f"Error in get_watchlist_performance API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate performance: {str(e)}"
        )

@router.get("/analytics", response_model=WatchlistAnalytics)
async def get_watchlist_analytics(
    virtual_investment: float = Query(10000.0, alias="virtualInvestment", gt=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve chart data and premium pick analytics cards.
    """
    try:
        analytics = await WatchlistService.get_watchlist_analytics(db, current_user.id, virtual_investment)
        return WatchlistAnalytics(
            best_pick=analytics["best_pick"],
            worst_pick=analytics["worst_pick"],
            fastest_gainer=analytics["fastest_gainer"],
            accuracy_percent=analytics["accuracy_percent"],
            winners_losers_chart=analytics["winners_losers_chart"],
            top_performers_chart=analytics["top_performers_chart"],
            roi_over_time_chart=analytics["roi_over_time_chart"]
        )
    except Exception as e:
        logger.error(f"Error in get_watchlist_analytics API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile analytics: {str(e)}"
        )
