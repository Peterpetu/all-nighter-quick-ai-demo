import os
import logging
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Type, TypeVar

from pydantic_ai import Agent

TDeps = TypeVar("TDeps")
TOutput = TypeVar("TOutput")

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base wrapper around pydantic_ai.Agent that:
      - explicitly injects OPENAI_API_KEY
      - holds a static system_prompt
      - supports per-call message injections
      - maintains a simple in-memory history
      - feeds chat_history back into the LLM for context
      - on any exception returns a fallback instance with `.error` set
    """

    def __init__(
        self,
        model: str,
        system_prompt: str,
        tools: Optional[List[Any]] = None,
        deps_type: Optional[Type[TDeps]] = None,
        output_type: Optional[Type[TOutput]] = None,
        memory_size: int = 10,
    ):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")

        self.system_prompt = system_prompt
        self.output_type = output_type

        agent_kwargs: Dict[str, Any] = {
            "model": model,
            "system_prompt": system_prompt,
            "tools": tools or [],
            "api_key": api_key,
        }
        if deps_type:
            agent_kwargs["deps_type"] = deps_type
        if output_type:
            agent_kwargs["output_type"] = output_type

        self.agent = Agent(**agent_kwargs)
        # deque of {"role": "user"/"assistant", "content": str}
        self.memory: Deque[Dict[str, str]] = deque(maxlen=memory_size)

    async def run(
        self,
        user_message: str,
        injections: Optional[Dict[str, str]] = None,
        deps: Optional[TDeps] = None,
    ) -> TOutput:
        """
        Run the agent on a user message, including:
          - injecting user_message (and any additional key:value lines)
          - passing the last N messages as chat_history
          - returning an instance of `output_type` with `.error` on failure
        """
        # 1. Record the raw user turn
        self.memory.append({"role": "user", "content": user_message})

        # 2. Build the prompt with optional injections
        lines: List[str] = []
        if injections:
            for k, v in injections.items():
                lines.append(f"{k}: {v}")
        lines.append(f"User message: {user_message}")
        full_message = "\n".join(lines)

        # 3. Call the LLM, feeding chat_history for context
        try:
            if deps is not None:
                result = await self.agent.run(
                    full_message,
                    deps=deps,
                    chat_history=list(self.memory),
                )
            else:
                result = await self.agent.run(
                    full_message,
                    chat_history=list(self.memory),
                )
            output = result.output
        except Exception as e:
            logger.error(
                "Agent %s failed: %s", self.__class__.__name__, e, exc_info=True
            )
            if self.output_type:
                return self.output_type(error=str(e))  # type: ignore
            raise RuntimeError("AI service unavailable") from e

        # 4. Record the assistant’s reply
        self.memory.append({"role": "assistant", "content": str(output)})
        return output
