from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.user_service_agent import UserServiceAgent, UserServiceOutput

router = APIRouter(prefix="/chat", tags=["chat"])

# Keep one orchestrator instance so its memory persists
_service_agent = UserServiceAgent()

class ChatRequest(BaseModel):
    message: str

@router.post("/", response_model=UserServiceOutput)
async def chat(req: ChatRequest):
    """
    Route all user messages to the UserServiceAgent.
    It will internally call support agents and optionally the manage_task tool.
    """
    try:
        return await _service_agent.run(req.message)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
