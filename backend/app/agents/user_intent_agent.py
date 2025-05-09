import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from .base import BaseAgent

logger = logging.getLogger(__name__)


class IntentEmotionOutput(BaseModel):
    intent: Optional[str] = Field(None, description="Detected user intent")
    emotion: Optional[str] = Field(None, description="Detected user emotional tone")
    error: Optional[str] = Field(None, description="Error message, if any")


class UserIntentAndEmotionAgent(BaseAgent):
    def __init__(self):
        prompt_path = Path(__file__).parent / "system_prompts" / "intent_emotion.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing system prompt: {prompt_path}")
        system_prompt = prompt_path.read_text(encoding="utf-8")

        super().__init__(
            model="openai:gpt-4o",
            system_prompt=system_prompt,
            tools=None,
            output_type=IntentEmotionOutput,
            memory_size=10,
        )
