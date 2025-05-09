import logging
from pathlib import Path
from typing import Optional, Dict, Union

from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from sqlmodel import select

from .base import BaseAgent # Make sure BaseAgent is correctly defined and uses pydantic_ai.Agent
from .task_creation_agent import TaskCreationAgent, TaskCreationOutput, TaskDeletionOutput
from .user_intent_agent import UserIntentAndEmotionAgent, IntentEmotionOutput
from .question_for_user_agent import QuestionForUserAgent, QuestionOutput
from .task_status_agent import TaskStatusAgent, StatusOutput
from app.db import get_session
from app.models import Task

logger = logging.getLogger(__name__)


class UserServiceOutput(BaseModel):
    """
    /chat response:
     - If a tool ran, `task` or `delete` is populated _and_ we include
       a confirmation in `chat_response`.
     - Otherwise, only `chat_response` holds the assistant’s reply.
    """
    task:           Optional[TaskCreationOutput]  = None
    delete:         Optional[TaskDeletionOutput]  = None
    intent:         IntentEmotionOutput
    question:       QuestionOutput
    status:         StatusOutput
    chat_response:  Optional[str]                  = Field(
        None,
        description="Human-friendly confirmation or chat reply"
    )


class UserServiceAgent(BaseAgent):
    def __init__(self) -> None:
        # Load orchestrator prompt
        prompt_path = Path(__file__).parent / "system_prompts" / "user_service.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing system prompt: {prompt_path}")
        system_prompt = prompt_path.read_text(encoding="utf-8")

        # Initialize BaseAgent: it will discover @self.agent.tool()
        super().__init__(
            model="openai:gpt-4.1",
            system_prompt=system_prompt,
            # Accept tool outputs _or_ plain text
            output_type=Union[TaskCreationOutput, TaskDeletionOutput, str],
            memory_size=50,
        )

        # Register manage_task tool
        @self.agent.tool
        async def manage_task(
            ctx: RunContext,
            command: str = Field(..., description="create/update/delete instruction")
        ) -> Union[TaskCreationOutput, TaskDeletionOutput]:
            return await TaskCreationAgent().run(command)

    async def run(
        self,
        user_message: str,
        injections: Optional[Dict[str, str]] = None,
        deps: Optional[int] = None,
    ) -> UserServiceOutput:
        # 1) Gather helper-agent context (intent, question, status)
        intent   = await UserIntentAndEmotionAgent().run(user_message)
        question = await QuestionForUserAgent().run(user_message)
        status   = await TaskStatusAgent().run(user_message)

        # 2) Inject the full list of existing tasks
        session = next(get_session())
        tasks = session.exec(select(Task)).all()
        existing = (
            "\n".join(
                f"{t.id}: {t.title} "
                f"(due {t.due_date.isoformat() if t.due_date else 'None'}, done={t.completed})"
                for t in tasks
            )
            or "No tasks yet."
        )

        # 3) Build prompt injections
        inj: Dict[str, str] = {
            "User intent/emotion": f"{intent.intent}|{intent.emotion}",
            "Suggested question":   question.question or "",
            "Task status summary":  status.status_summary or "",
            "Existing tasks":       existing,
        }
        if injections:
            inj.update(injections)

        # 4) Let the orchestrator LLM run:
        result = await super().run(user_message, injections=inj, deps=deps)

        # 5) If the tool ran: result is a TaskCreationOutput or TaskDeletionOutput
        if isinstance(result, TaskCreationOutput):
            # Craft a human-friendly confirmation
            confirm = (
                f"✅ Created task #{result.id}: “{result.title}”"
                + (f" due {result.due_date}" if result.due_date else "")
            )
            return UserServiceOutput(
                task=result,
                delete=None,
                intent=intent,
                question=question,
                status=status,
                chat_response=confirm,
            )

        if isinstance(result, TaskDeletionOutput):
            confirm = (
                f"🗑️ Deleted task #{result.id}"
                if result.deleted else f"❌ Could not delete task #{result.id}"
            )
            return UserServiceOutput(
                task=None,
                delete=result,
                intent=intent,
                question=question,
                status=status,
                chat_response=confirm,
            )

        # 6) Otherwise: plain-text chat (result is string)
        return UserServiceOutput(
            task=None,
            delete=None,
            intent=intent,
            question=question,
            status=status,
            chat_response=str(result),
        )