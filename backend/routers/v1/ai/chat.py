from fastapi import APIRouter, Depends
from models import User
from schemas import AIPromptRequest, AIPromptResponse
from utils.auth import get_current_user
from services.ai_service import get_ai_service

router = APIRouter(prefix="/chat", tags=["AI Chat"])
ai_service = get_ai_service()

@router.post("/prompt", response_model=AIPromptResponse)
async def process_ai_prompt(request: AIPromptRequest, current_user: User = Depends(get_current_user)):
    results = await ai_service.process_prompt(request.prompt, getattr(current_user, "upstox_access_token", None))
    return {
        "status": "success",
        "recommendations": results
    }
