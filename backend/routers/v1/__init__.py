from fastapi import APIRouter
from .ai import router as ai_router
from .trading import router as trading_router
from .orders import router as orders_router
from .market import router as market_router
from .auth import router as auth_router
from .users import router as users_router
from .admin import router as admin_router

router = APIRouter(prefix="/v1")

router.include_router(ai_router)
router.include_router(trading_router)
router.include_router(orders_router)
router.include_router(market_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(admin_router)
