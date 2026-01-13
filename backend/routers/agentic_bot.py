
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from models import User
from utils.auth import get_current_user
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy init orchestrator to avoid import errors at startup
_orchestrator = None

def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from agents.orchestrator import AgentOrchestrator
        _orchestrator = AgentOrchestrator()
    return _orchestrator

class AgentRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="Analysis prompt")

@router.post("/analyze")
async def run_agent_analysis(
    request: AgentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Trigger the 3-Agent Workflow
    """
    try:
        orchestrator = get_orchestrator()
        result = await asyncio.wait_for(orchestrator.run_workflow(request.prompt), timeout=60.0)
        return result
    except asyncio.TimeoutError:
        logger.warning("Agent analysis timed out")
        return {
            "status": "timeout",
            "message": "Agent workflow timed out. Please try a simpler query.",
            "stocks": []
        }
    except Exception as e:
        logger.error(f"Agent analysis failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "stocks": []
        }

@router.post("/process")
async def process_agent_request(request: AgentRequest):
    """
    Alias for /analyze - Process agent request
    """
    return await run_agent_analysis(request)

