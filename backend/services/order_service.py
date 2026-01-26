import logging
import httpx
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import User, Order, UserSettings, Position
from schemas import OrderCreate, OrderResponse
from services.dragonfly_client import get_cache
from services.live_price_enricher import get_single_live_price

logger = logging.getLogger(__name__)

class OrderService:
    async def create_order(
        self, 
        order: OrderCreate, 
        current_user: User, 
        db: AsyncSession
    ) -> Order:
        """Create a new order with risk validation and duplicate detection."""
        if not current_user.is_upstox_connected:
            raise ValueError("Upstox not connected")
        
        # 1. Duplicate Order Detection (60s window)
        cache = get_cache()
        dedup_key = f"qai:order_dedup:{current_user.id}:{order.symbol}:{order.quantity}:{order.order_type}"
        if cache.is_available() and cache.get(dedup_key):
            raise ValueError("Duplicate order detected. Please wait 60 seconds before placing the same order.")

        # 2. Risk Validation
        settings_res = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
        settings = settings_res.scalar_one_or_none()
        if not settings:
            raise ValueError("User risk settings not found")

        current_price = order.price or await get_single_live_price(order.symbol)
        if not current_price:
            raise ValueError(f"Could not fetch current price for {order.symbol} to validate risk")
        
        order_cost = order.quantity * current_price
        
        if order_cost > settings.max_capital:
            raise ValueError(f"Order cost ({order_cost:.2f}) exceeds your maximum allowed capital ({settings.max_capital})")

        pos_res = await db.execute(select(func.sum(Position.avg_price * Position.quantity)).where(Position.user_id == current_user.id))
        used_capital = pos_res.scalar() or 0.0
        available_capital = settings.max_capital - used_capital
        
        if order_cost > available_capital:
            raise ValueError(f"Insufficient available capital. Required: {order_cost:.2f}, Available: {available_capital:.2f} (Used: {used_capital:.2f}, Max: {settings.max_capital})")

        max_trade_exposure = settings.max_capital * (settings.max_risk_per_trade / 100)
        if order_cost > max_trade_exposure:
             raise ValueError(f"Order exposure ({order_cost:.2f}) exceeds your risk-per-trade limit ({max_trade_exposure:.2f})")

        # 3. Upstox API Call
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
                upstox_data = response.json()
                
                # 4. Success -> Create DB record
                db_order = Order(
                    user_id=current_user.id,
                    symbol=order.symbol,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    price=order.price,
                    status="PENDING",
                    order_id=upstox_data.get("data", {}).get("order_id", "")
                )
                db.add(db_order)
                
                if cache.is_available():
                    cache.set(dedup_key, "1", ttl=60)
                    
                await db.commit()
                await db.refresh(db_order)
                return db_order
            except httpx.HTTPStatusError as e:
                logger.error(f"Upstox order failed: {e.response.text}")
                raise ValueError(f"Upstox API error: {e.response.text}")
            except Exception as e:
                logger.error(f"Order placement error: {str(e)}")
                raise ValueError(f"Internal error: {str(e)}")

    async def get_user_orders(self, user_id: int, db: AsyncSession) -> List[Order]:
        """Fetch all orders for a user."""
        result = await db.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.timestamp.desc())
        )
        return result.scalars().all()

    async def get_order_by_id(self, order_id: int, user_id: int, db: AsyncSession) -> Optional[Order]:
        """Fetch a specific order by ID."""
        result = await db.execute(
            select(Order).where(Order.id == order_id, Order.user_id == user_id)
        )
        return result.scalar_one_or_none()

_order_service = None
def get_order_service():
    global _order_service
    if _order_service is None:
        _order_service = OrderService()
    return _order_service
