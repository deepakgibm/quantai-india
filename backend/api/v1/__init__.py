from fastapi import APIRouter
from .quant_workspace import router as quant_workspace_router
from .walk_forward import router as walk_forward_router

router = APIRouter()

router.include_router(quant_workspace_router, prefix="/quant")
router.include_router(walk_forward_router, prefix="/walk-forward")


