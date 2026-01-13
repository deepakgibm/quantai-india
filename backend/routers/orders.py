from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import httpx

from database import get_db
from models import User, Order, UserSettings, Position
from schemas import OrderCreate, OrderResponse
from utils.auth import get_current_user
from services.dragonfly_client import get_cache
from services.live_price_enricher import get_single_live_price
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_upstox_connected:
        raise HTTPException(status_code=400, detail="Upstox not connected")
    
    # HP-9: Duplicate Order Detection (60s window per user/symbol/quantity/type)
    cache = get_cache()
    dedup_key = f"qai:order_dedup:{current_user.id}:{order.symbol}:{order.quantity}:{order.order_type}"
    if cache.is_available() and cache.get(dedup_key):
        raise HTTPException(status_code=400, detail="Duplicate order detected. Please wait 60 seconds before placing the same order.")

    # HP-8: Risk Validation
    # 1. Fetch user risk settings
    res = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    settings = res.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=400, detail="User risk settings not found")

    # 2. Estimate order cost
    current_price = order.price
    if not current_price:
        # Fetch live price for estimation
        current_price = await get_single_live_price(order.symbol)
        if not current_price:
            raise HTTPException(status_code=400, detail=f"Could not fetch current price for {order.symbol} to validate risk")
    
    order_cost = order.quantity * current_price
    
    # 3. Check against max_capital
    if order_cost > settings.max_capital:
        raise HTTPException(status_code=400, detail=f"Order cost ({order_cost:.2f}) exceeds your maximum allowed capital ({settings.max_capital})")

    # 4. Check available capital (Optional but recommended)
    # Fetch current positions to calculate used capital
    from sqlalchemy import func
    pos_res = await db.execute(select(func.sum(Position.avg_price * Position.quantity)).where(Position.user_id == current_user.id))
    used_capital = pos_res.scalar() or 0.0
    available_capital = settings.max_capital - used_capital
    
    if order_cost > available_capital:
        raise HTTPException(status_code=400, detail=f"Insufficient available capital. Required: {order_cost:.2f}, Available: {used_capital:.2f} (Max: {settings.max_capital})")

    # 5. Check risk per trade (e.g. if SL is defined, otherwise we use total capital exposure)
    # Here we'll just check if the position size is reasonable per risk settings
    max_trade_exposure = settings.max_capital * (settings.max_risk_per_trade / 100)
    # Note: Traditional risk per trade involves SL, but here we'll use a simple exposure cap as a proxy if SL is missing
    if order_cost > max_trade_exposure:
         raise HTTPException(status_code=400, detail=f"Order exposure ({order_cost:.2f}) exceeds your risk-per-trade limit ({max_trade_exposure:.2f})")
    headers = {
        "Authorization": f"Bearer {current_user.upstox_access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    upstox_order = {
        "quantity": order.quantity,
        "product": "D",
        "validity": "DAY",
        "price": order.price if order.price else 0,
        "tag": "QuantAI",
        "instrument_token": order.symbol,
        "order_type": "MARKET" if not order.price else "LIMIT",
        "transaction_type": order.order_type,
        "disclosed_quantity": 0,
        "trigger_price": 0,
        "is_amo": False
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.upstox.com/v2/order/place",
                headers=headers,
                json=upstox_order
            )
            response.raise_for_status()
            upstox_response = response.json()
            
            db_order = Order(
                user_id=current_user.id,
                symbol=order.symbol,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                status="PENDING",
                order_id=upstox_response.get("data", {}).get("order_id", "")
            )
            db.add(db_order)
            
            # Set dedup key in cache
            if cache.is_available():
                cache.set(dedup_key, "1", ttl=60)
                
            await db.commit()
            await db.refresh(db_order)
            
            return db_order
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=400, detail=f"Order placement failed: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Order placement failed: {str(e)}")

@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id).order_by(Order.timestamp.desc())
    )
    orders = result.scalars().all()
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
