from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import requests

from database import get_db
from models import User, Order
from schemas import OrderCreate, OrderResponse
from utils.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_upstox_connected:
        raise HTTPException(status_code=400, detail="Upstox not connected")
    
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
    
    try:
        response = requests.post(
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
        await db.commit()
        await db.refresh(db_order)
        
        return db_order
    except requests.RequestException as e:
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
