import logging
from pathlib import Path
from typing import Optional, Dict, Union

from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from sqlmodel import select

from app.agents.base import BaseAgent
from app.agents.task_creation_agent import TaskCreationAgent
from app.agents.user_intent_agent import UserIntentAndEmotionAgent, IntentEmotionOutput
from app.agents.question_for_user_agent import QuestionForUserAgent, QuestionOutput
from app.agents.task_status_agent import TaskStatusAgent, StatusOutput
from app.db import get_session
from app.models import Task

logger = logging.getLogger(__name__)


class UserServiceOutput(BaseModel):
    """
    /chat response structure:
      - If we invoked the TaskCreationAgent, the plain text from that sub-agent is included in chat_response.
      - Otherwise, chat_response is just the orchestrator's direct message.
      - We also include the sub-agent results from intent, question, status for reference.
    """
    intent:         IntentEmotionOutput
    question:       QuestionOutput
    status:         StatusOutput
    chat_response:  Optional[str] = Field(
        None,
        description="Human-friendly confirmation or chat reply"
    )

class UserServiceAgent(BaseAgent):
    def __init__(self) -> None:
        # Load orchestrator prompt (updated to mention we have only one tool: talk_to_task_creation_agent)
        prompt_path = Path(__file__).parent / "system_prompts" / "user_service.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing system prompt: {prompt_path}")
        system_prompt = prompt_path.read_text(encoding="utf-8")

        # Initialize BaseAgent: single tool returns plain text from sub-agent
        super().__init__(
            model="openai:gpt-4o",
            system_prompt=system_prompt,
            # The final output from this agent can be either a direct string or a tool response (string),
            # but we store it in the pydantic output model below (UserServiceOutput).
            output_type=str,
            memory_size=100,
        )

        # Register a single tool: talk_to_task_creation_agent
        @self.agent.tool
        async def talk_to_task_creation_agent(
            ctx: RunContext,
            instruction: str = Field(..., description="A free-form request to create/update/delete tasks.")
        ) -> str:
            """
            The orchestrator calls this tool to communicate with the TaskCreationAgent using plain English.
            TaskCreationAgent will internally use create/update/delete sub-tools as needed, then return text.
            """
            logger.info(f"[UserServiceAgent] talk_to_task_creation_agent invoked with instruction: {instruction}")
            response = await TaskCreationAgent().run(instruction)
            # Ensure we return a pure string
            return response if isinstance(response, str) else str(response)

    async def run(
        self,
        user_message: str,
        injections: Optional[Dict[str, str]] = None,
        deps: Optional[int] = None,
    ) -> UserServiceOutput:
        """
        The main flow:
          1) Use sub-agents to gather context: intent/emotion, clarifying question, task status summary.
          2) Build prompt injections with these sub-agent outputs + existing tasks from the DB.
          3) Let the LLM produce either a direct text reply, or invoke the 'talk_to_task_creation_agent' tool.
          4) Return a structured output with the final chat_response plus the sub-agents' data.
        """

        # 1) Gather helper-agent context
        intent   = await UserIntentAndEmotionAgent().run(user_message)
        question = await QuestionForUserAgent().run(user_message)
        status   = await TaskStatusAgent().run(user_message)

        # 2) Get existing tasks for the injection
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

        logger.info(f"[UserServiceAgent] prompt injections: {inj}")

        # 4) Let the orchestrator LLM run. We expect a string output.
        result_str = await super().run(user_message, injections=inj, deps=deps)

        # 5) Wrap everything in the final pydantic output
        return UserServiceOutput(
            intent=intent,
            question=question,
            status=status,
            chat_response=str(result_str),
        )
