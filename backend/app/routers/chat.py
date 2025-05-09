import logging
from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.task_creation_agent import TaskCreationAgent, TaskCreationOutput

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    data: TaskCreationOutput


@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Always return a structured TaskCreationOutput (with .error if something went wrong).
    """
    agent = TaskCreationAgent()
    try:
        result = await agent.run(req.message)
    except Exception as e:
        # Fallback if something very unexpected happens
        logger.error("Chat handler unexpected error: %s", e, exc_info=True)
        result = TaskCreationOutput(error="Internal error; please try again later")

    return ChatResponse(data=result)
