from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from models import User
from utils.auth import get_current_user
from services.index_admin_service import get_index_admin_service

router = APIRouter(prefix="/indices", tags=["Admin (v1)"])
admin_service = get_index_admin_service()

# Note: In a real app, we'd check if user.is_admin
# For now, we'll just require authentication

@router.post("/")
async def create_index(
    name: str, 
    description: str = "", 
    base_index_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return await admin_service.create_index(db, name, description, base_index_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{index_id}/constituents/{symbol}")
async def add_constituent(
    index_id: int, 
    symbol: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        await admin_service.add_constituent(db, index_id, symbol)
        return {"status": "success", "message": f"Added {symbol} to index {index_id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{index_id}/constituents/{symbol}")
async def remove_constituent(
    index_id: int, 
    symbol: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        await admin_service.remove_constituent(db, index_id, symbol)
        return {"status": "success", "message": f"Removed {symbol} from index {index_id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{index_id}")
async def delete_index(
    index_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await admin_service.delete_index(db, index_id)
    return {"status": "success", "message": f"Index {index_id} deleted"}
