from fastapi import APIRouter, Depends
from models import User
from schemas import MarketAnalysisResponse
from utils.auth import get_current_user
from services.ai_service import get_ai_service

router = APIRouter(prefix="/analysis", tags=["AI Analysis"])
ai_service = get_ai_service()

@router.get("/market", response_model=MarketAnalysisResponse)
async def get_market_analysis(current_user: User = Depends(get_current_user)):
    return await ai_service.get_market_analysis()
