"""Base Agent class implementing the ReAct pattern."""

from __future__ import annotations
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from backend.models import AgentEvent, AgentType
from backend.config import OLLAMA_BASE_URL, MODEL_NAME, DEMO_MODE

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base agent with ReAct (Reason + Act) loop.

    Each agent:
    1. Receives context from the orchestrator
    2. Reasons about the task using Claude
    3. Executes tools as needed
    4. Returns structured results
    """

    def __init__(self, event_callback: Optional[Callable] = None):
        self._event_callback = event_callback
        self._client = None

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """The type of this agent."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this agent."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt defining the agent's role and capabilities."""
        ...

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's task with the given context."""
        ...

    def _get_client(self):
        """No client needed for simple HTTP to local Ollama API."""
        return None

    async def _call_llm(self, prompt: str, max_tokens: int = 4096) -> str:
        """Call Local LLM via plain HTTP (e.g., Ollama)."""
        if DEMO_MODE:
            return self._get_demo_response(prompt)

        import urllib.request
        import json

        data = {
            "model": MODEL_NAME,
            "prompt": f"{self.system_prompt}\n\n{prompt}",
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }
        req = urllib.request.Request(
            OLLAMA_BASE_URL,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            def fetch():
                with urllib.request.urlopen(req) as response:
                    return json.loads(response.read().decode("utf-8"))

            res_json = await asyncio.to_thread(fetch)
            return res_json.get("response", "")
        except Exception as e:
            logger.error(f"[{self.name}] LLM call failed: {e}")
            return f"Error: {e}"

    def _get_demo_response(self, prompt: str) -> str:
        """Return a demo response — overridden by subclasses."""
        return "{}"

    async def emit_event(self, event_type: str, title: str,
                         detail: str = "", data: dict = None):
        """Emit a real-time event for the dashboard."""
        event = AgentEvent(
            agent=self.agent_type,
            event_type=event_type,
            title=title,
            detail=detail,
            data=data or {}
        )
        if self._event_callback:
            await self._event_callback(event)
        # In demo mode, add delay so WebSocket can stream events visibly
        if DEMO_MODE:
            await asyncio.sleep(0.35)
        return event
