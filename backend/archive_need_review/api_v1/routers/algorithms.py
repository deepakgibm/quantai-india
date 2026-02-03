from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from database import get_db
from models import User, Algorithm
from schemas import AlgorithmCreate, AlgorithmUpdate, AlgorithmResponse
from utils.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=AlgorithmResponse)
async def create_algorithm(
    algorithm: AlgorithmCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    db_algorithm = Algorithm(
        user_id=current_user.id,
        name=algorithm.name,
        description=algorithm.description,
        config=algorithm.config,
        is_active=False,
        performance=0.0
    )
    db.add(db_algorithm)
    await db.commit()
    await db.refresh(db_algorithm)
    return db_algorithm

@router.get("/", response_model=List[AlgorithmResponse])
async def get_algorithms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Algorithm).where(Algorithm.user_id == current_user.id)
    )
    algorithms = result.scalars().all()
    
    if not algorithms:
        # Default algorithms for new user
        default_algos = [
            {
                "name": "Trend Finder AI",
                "description": "Identifies strong trend continuation setups",
                "is_active": True,
                "performance": 12.4,
                "config": {"timeframe": "15m", "indicators": ["EMA", "RSI"]}
            },
            {
                "name": "Breakout Detector",
                "description": "Catches volume-backed breakouts in real-time",
                "is_active": False,
                "performance": 8.2,
                "config": {"volume_threshold": 1.5, "breakout_percentage": 2.0}
            },
            {
                "name": "Top 3 Buy/Sell Engine",
                "description": "Auto-picks 3 best stocks daily 9:30-3:15",
                "is_active": True,
                "performance": 18.7,
                "config": {"max_stocks": 3, "scan_interval": "5m"}
            }
        ]
        
        for algo_data in default_algos:
            algo = Algorithm(user_id=current_user.id, **algo_data)
            db.add(algo)
        
        await db.commit()
        result = await db.execute(
            select(Algorithm).where(Algorithm.user_id == current_user.id)
        )
        algorithms = result.scalars().all()
    
    return algorithms

@router.get("/{algorithm_id}", response_model=AlgorithmResponse)
async def get_algorithm(
    algorithm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Algorithm).where(
            Algorithm.id == algorithm_id,
            Algorithm.user_id == current_user.id
        )
    )
    algorithm = result.scalar_one_or_none()
    if not algorithm:
        raise HTTPException(status_code=404, detail="Algorithm not found")
    return algorithm

@router.put("/{algorithm_id}", response_model=AlgorithmResponse)
async def update_algorithm(
    algorithm_id: int,
    algorithm_update: AlgorithmUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Algorithm).where(
            Algorithm.id == algorithm_id,
            Algorithm.user_id == current_user.id
        )
    )
    algorithm = result.scalar_one_or_none()
    if not algorithm:
        raise HTTPException(status_code=404, detail="Algorithm not found")
    
    if algorithm_update.name is not None:
        algorithm.name = algorithm_update.name
    if algorithm_update.description is not None:
        algorithm.description = algorithm_update.description
    if algorithm_update.is_active is not None:
        algorithm.is_active = algorithm_update.is_active
    if algorithm_update.config is not None:
        algorithm.config = algorithm_update.config
    
    await db.commit()
    await db.refresh(algorithm)
    return algorithm

@router.delete("/{algorithm_id}")
async def delete_algorithm(
    algorithm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Algorithm).where(
            Algorithm.id == algorithm_id,
            Algorithm.user_id == current_user.id
        )
    )
    algorithm = result.scalar_one_or_none()
    if not algorithm:
        raise HTTPException(status_code=404, detail="Algorithm not found")
    
    await db.delete(algorithm)
    await db.commit()
    return {"message": "Algorithm deleted successfully"}
