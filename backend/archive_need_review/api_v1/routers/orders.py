from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db
from models import User
from schemas import OrderCreate, OrderResponse
from utils.auth import get_current_user
from services.order_service import get_order_service

router = APIRouter()
order_service = get_order_service()

@router.post("/", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await order_service.create_order(order, current_user, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Order placement failed")

@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await order_service.get_user_orders(current_user.id, db)

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    order = await order_service.get_order_by_id(order_id, current_user.id, db)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
