from fastapi import APIRouter
from .walk_forward import router as walk_forward_router
from .experiment_lab import router as experiment_lab_router
from .backtest_strategies import router as backtest_strategies_router

router = APIRouter()

router.include_router(walk_forward_router)
router.include_router(experiment_lab_router)
router.include_router(backtest_strategies_router)
