import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from .base import BaseAgent

logger = logging.getLogger(__name__)


class QuestionOutput(BaseModel):
    question: Optional[str] = Field(None, description="Clarifying question for the user")
    error: Optional[str] = Field(None, description="Error message, if any")


class QuestionForUserAgent(BaseAgent):
    def __init__(self):
        prompt_path = Path(__file__).parent / "system_prompts" / "question_for_user.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing system prompt: {prompt_path}")
        system_prompt = prompt_path.read_text(encoding="utf-8")

        super().__init__(
            model="openai:gpt-4o",
            system_prompt=system_prompt,
            tools=None,
            output_type=QuestionOutput,
            memory_size=50,
        )
