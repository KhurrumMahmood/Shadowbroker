"""SubAgent — a focused LLM agent with scoped tools and bounded execution."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from services.agent.llm import call_llm_simple
from services.agent.registry import create_default_registry
from services.agent.router import SubTask

logger = logging.getLogger(__name__)

_DEFAULT_DEADLINE_SECONDS = 30.0


@dataclass
class SubAgentResult:
    """Result from a sub-agent execution."""
    sub_task_intent: str
    summary: str
    key_findings: list[str] = field(default_factory=list)
    entity_references: list[dict] = field(default_factory=list)
    tool_calls_made: list[dict] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    duration_ms: int = 0


class SubAgent:
    """Focused LLM agent with scoped tools. Designed for ThreadPoolExecutor."""

    def __init__(
        self,
        provider: dict,
        sub_task: SubTask,
        ds,
        deadline: float = 0.0,
        max_tool_rounds: int = 2,
    ):
        self.provider = provider
        self.sub_task = sub_task
        self.ds = ds
        self.deadline = deadline or (time.monotonic() + _DEFAULT_DEADLINE_SECONDS)
        self.max_tool_rounds = max_tool_rounds
        self._registry = create_default_registry()

    def run(self) -> SubAgentResult:
        """Execute the sub-agent. Synchronous — safe for ThreadPoolExecutor."""
        start = time.monotonic()
        intent = self.sub_task.intent

        try:
            result = self._execute()
            result.duration_ms = int((time.monotonic() - start) * 1000)
            return result
        except Exception as e:
            logger.warning(f"SubAgent {intent} failed: {e}")
            return SubAgentResult(
                sub_task_intent=intent,
                summary="",
                success=False,
                error=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    def _execute(self) -> SubAgentResult:
        intent = self.sub_task.intent
        tools = self._registry.get_tool_schemas()
        messages = self._build_messages()

        def tool_executor(name: str, args: dict) -> str:
            return self._registry.execute(name, args, ds=self.ds)

        llm_result = call_llm_simple(
            provider=self.provider,
            messages=messages,
            tools=tools,
            tool_executor=tool_executor,
            deadline=self.deadline,
            max_tool_rounds=self.max_tool_rounds,
        )

        if llm_result["error"]:
            return SubAgentResult(
                sub_task_intent=intent,
                summary="",
                success=False,
                error=llm_result["error"],
                tool_calls_made=llm_result["tool_calls_made"],
            )

        # Parse the LLM's response as JSON
        content = llm_result["content"]
        parsed = self._parse_response(content)

        return SubAgentResult(
            sub_task_intent=intent,
            summary=parsed.get("summary", content),
            key_findings=parsed.get("key_findings", []),
            entity_references=parsed.get("entity_references", []),
            tool_calls_made=llm_result["tool_calls_made"],
            success=True,
        )

    def _build_messages(self) -> list[dict]:
        system_prompt = (
            f"You are a specialized analyst. "
            f"Analyze the following using your available tools and respond with JSON:\n"
            f'{{"summary": "...", "key_findings": ["..."], "entity_references": '
            f'[{{"type": "...", "id": "..."}}]}}\n'
            f"Focus on: {self.sub_task.query_fragment}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self.sub_task.query_fragment},
        ]

    def _parse_response(self, content: str) -> dict:
        """Try to parse JSON from the LLM response."""
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            import re
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
            return {"summary": content}
