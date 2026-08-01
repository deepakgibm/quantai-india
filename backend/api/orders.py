from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User, Order
from utils.auth import get_current_user
from sqlalchemy import select

router = APIRouter(tags=["Orders"])

@router.get("/")
async def get_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(Order).where(Order.user_id == current_user.id).order_by(Order.timestamp.desc())
        res = await db.execute(stmt)
        orders = list(res.scalars().all())
        serialized = []
        for o in orders:
            serialized.append({
                "id": o.id,
                "user_id": o.user_id,
                "symbol": o.symbol,
                "order_type": o.order_type,
                "quantity": o.quantity,
                "price": o.price,
                "status": o.status,
                "order_id": o.order_id,
                "timestamp": o.timestamp.isoformat() if o.timestamp else None
            })
        return {
            "status": "success",
            "orders": serialized
        }
    except Exception:
        return {"status": "success", "orders": []}
