from fastapi import APIRouter
from .indices import router as indices_router

router = APIRouter(prefix="/admin")
router.include_router(indices_router)
