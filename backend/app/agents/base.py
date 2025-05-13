# file: app/agents/base.py

import os
import logging
import json
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
      - supports manual memory injection into the final prompt
      - maintains a simple in-memory conversation history
      - performs JSON-based "agent tracing" after each run
    """

    def __init__(
        self,
        model: str,
        system_prompt: str,
        tools: Optional[List[Any]] = None,
        deps_type: Optional[Type[TDeps]] = None,
        output_type: Optional[Type[TOutput]] = None,
        memory_size: int = 50,
    ):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")

        self.system_prompt = system_prompt
        self.output_type = output_type

        agent_kwargs: Dict[str, Any] = {
            "model": model,
            "system_prompt": system_prompt,  # also used by pydantic_ai
            "tools": tools or [],
            "api_key": api_key,
        }
        if deps_type:
            agent_kwargs["deps_type"] = deps_type
        if output_type:
            agent_kwargs["output_type"] = output_type

        self.agent = Agent(**agent_kwargs)

        # We'll store each message in memory as: {"role": "user"/"assistant", "content": "..."}
        self.memory: Deque[Dict[str, str]] = deque(maxlen=memory_size)

    async def run(
        self,
        user_message: str,
        injections: Optional[Dict[str, str]] = None,
        deps: Optional[TDeps] = None,
    ) -> TOutput:
        """
        Build a final prompt with:
          1) System prompt at the top.
          2) Entire conversation so far (self.memory).
          3) Additional context (injections).
        Then pass it to the LLM as a single text block.

        After we get a result, we do JSON-based tracing with flush=True.
        """

        # Step 1) Save the new user message into memory
        self.memory.append({"role": "user", "content": user_message})

        # Step 2) Build the final prompt
        prompt_lines: List[str] = []
        prompt_lines.append(f"System Prompt:\n{self.system_prompt}\n")

        prompt_lines.append("Conversation So Far:")
        for turn in self.memory:
            role_label = "User" if turn["role"] == "user" else "Assistant"
            prompt_lines.append(f"{role_label}: {turn['content']}")

        # Add any additional context
        if injections:
            prompt_lines.append("\nAdditional Context:")
            for k, v in injections.items():
                prompt_lines.append(f"{k}: {v}")

        final_prompt = "\n".join(prompt_lines)

        # Optional debug print of the final prompt
        # print(f"[DEBUG] Final Prompt for {self.__class__.__name__}:\n{final_prompt}\n", flush=True)

        # Step 3) Try to run the LLM
        try:
            result = await self.agent.run(
                final_prompt,
                deps=deps,
                # Not passing chat_history=... since we embed memory ourselves
            )
            output = result.output
        except Exception as e:
            logger.error(
                "Agent %s failed: %s", self.__class__.__name__, e, exc_info=True
            )
            if self.output_type:
                # Return an instance with .error if your output_type has that field
                return self.output_type(error=str(e))  # type: ignore
            raise RuntimeError("AI service unavailable") from e

        # Step 4) Save assistant’s reply in memory
        self.memory.append({"role": "assistant", "content": str(output)})

        # Step 5) Perform JSON-based "agent tracing" 
        # We'll gather relevant data into a dict and print it with flush=True
        trace_data = {
            "agent_class": self.__class__.__name__,
            "final_prompt": final_prompt,
            "model_output": str(output),
            "user_message": user_message,
            "memory_size": len(self.memory),
            "injections": injections or {},
        }
        # If your output_type is a pydantic model, we could add more info like error fields or success flags

        print(json.dumps(trace_data, indent=2), flush=True)

        # Finally, return the output
        return output
