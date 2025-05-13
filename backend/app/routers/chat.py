from fastapi import APIRouter, HTTPException
# JSONResponse is no longer needed here if we always return UserServiceOutput for 200 OK
from pydantic import BaseModel

from app.agents.user_service_agent import UserServiceAgent, UserServiceOutput
from app.guardrails import PromptSafetyFilter

# Import the sub-agent output models to construct the response
# These imports are necessary to create a valid UserServiceOutput object
from app.agents.user_intent_agent import IntentEmotionOutput
from app.agents.question_for_user_agent import QuestionOutput
from app.agents.task_status_agent import StatusOutput


router = APIRouter(prefix="/chat", tags=["chat"])

_service_agent = UserServiceAgent()
_prompt_safety_filter = PromptSafetyFilter()

class ChatRequest(BaseModel):
    message: str

@router.post("/", response_model=UserServiceOutput)
async def chat(req: ChatRequest):
    """
    Route all user messages to the UserServiceAgent.
    It will internally call support agents and optionally the manage_task tool.
    First, a prompt safety check is performed.
    """
    if _prompt_safety_filter.is_unsafe(req.message):
        intent_placeholder = IntentEmotionOutput(intent="N/A", emotion="N/A")
        
        question_placeholder = QuestionOutput(question=None)
        

        status_placeholder = StatusOutput(status_summary=None)

        guardrail_response = UserServiceOutput(
            intent=intent_placeholder,
            question=question_placeholder,
            status=status_placeholder,
            chat_response="Your input contains forbidden keywords and cannot be processed. Please rephrase your request."
        )
        return guardrail_response # FastAPI will serialize this and send a 200 OK
    
    try:
        return await _service_agent.run(req.message)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))