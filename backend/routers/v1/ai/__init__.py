from fastapi import APIRouter
from .chat import router as chat_router
from .scanners import router as scanners_router
from .analysis import router as analysis_router

router = APIRouter(prefix="/ai", tags=["AI (v1)"])

router.include_router(chat_router)
router.include_router(scanners_router)
router.include_router(analysis_router)
