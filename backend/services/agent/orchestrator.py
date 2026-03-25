"""Orchestrator — dispatches sub-agents in parallel, collects and synthesizes results."""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from services.agent.llm import call_llm_simple
from services.agent.router import QueryPlan, SubTask
from services.agent.sub_agent import SubAgent, SubAgentResult

logger = logging.getLogger(__name__)

_MAX_WORKERS = 3
_AGENT_TIME_BUDGET_RATIO = 0.7  # 70% of total time for agents, 30% reserved


def _sse(event: str, data: dict) -> str:
    """Format a single SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@dataclass
class OrchestratorResult:
    """Final result from orchestrated compound query."""
    summary: str
    sub_results: list[SubAgentResult] = field(default_factory=list)
    plan: QueryPlan | None = None
    layers: dict | None = None
    viewport: dict | None = None
    result_entities: list[dict] = field(default_factory=list)
    filters: dict | None = None
    reasoning_steps: list[dict] = field(default_factory=list)
    duration_ms: int = 0
    provider: str = ""


class Orchestrator:
    """Dispatches sub-agents for compound queries, synthesizes results."""

    def __init__(
        self,
        provider: dict,
        ds,
        total_budget_seconds: float = 30.0,
        use_llm_synthesis: bool = False,
    ):
        self.provider = provider
        self.ds = ds
        self.total_budget = total_budget_seconds
        self.use_llm_synthesis = use_llm_synthesis

    def run(self, query: str, plan: QueryPlan) -> OrchestratorResult:
        """Execute a compound query plan.

        1. Dispatch sub-agents in parallel (ThreadPoolExecutor)
        2. Collect results
        3. Synthesize (deterministic concatenation for now)
        """
        start = time.monotonic()
        agent_deadline = start + (self.total_budget * _AGENT_TIME_BUDGET_RATIO)

        # Filter out synthesis sub-tasks — those are handled here, not by sub-agents
        agent_tasks = [t for t in plan.sub_tasks if t.intent != "synthesis"]

        sub_results = self._dispatch_parallel(agent_tasks, agent_deadline)
        result = self._synthesize(query, sub_results, plan)
        result.duration_ms = int((time.monotonic() - start) * 1000)
        result.provider = self.provider.get("model", "")

        return result

    def run_streaming(self, query: str, plan: QueryPlan):
        """Generator that yields SSE event strings with progressive updates.

        Event types:
          - plan: query decomposition (emitted immediately)
          - sub_result: each sub-agent completion
          - result: final synthesized result
        """
        start = time.monotonic()
        agent_deadline = start + (self.total_budget * _AGENT_TIME_BUDGET_RATIO)

        # Emit plan event
        yield _sse("plan", {
            "complexity": plan.complexity.value,
            "sub_tasks": [
                {"intent": t.intent, "description": t.query_fragment}
                for t in plan.sub_tasks
            ],
        })

        # Dispatch sub-agents and yield results as they complete
        agent_tasks = [t for t in plan.sub_tasks if t.intent != "synthesis"]
        sub_results = []

        if agent_tasks:
            with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(agent_tasks))) as executor:
                futures = {}
                for task in agent_tasks:
                    agent = SubAgent(
                        provider=self.provider,
                        sub_task=task,
                        ds=self.ds,
                        deadline=agent_deadline,
                    )
                    future = executor.submit(agent.run)
                    futures[future] = task

                for future in as_completed(futures, timeout=max(0, agent_deadline - time.monotonic())):
                    try:
                        result = future.result()
                    except Exception as e:
                        task = futures[future]
                        result = SubAgentResult(
                            sub_task_intent=task.intent,
                            summary="",
                            success=False,
                            error=str(e),
                        )
                    sub_results.append(result)

                    yield _sse("sub_result", {
                        "sub_task": result.sub_task_intent,
                        "summary": result.summary,
                        "success": result.success,
                        "duration_ms": result.duration_ms,
                    })

        # Synthesize and emit final result
        final = self._synthesize(query, sub_results, plan)
        final.duration_ms = int((time.monotonic() - start) * 1000)
        final.provider = self.provider.get("model", "")

        yield _sse("result", {
            "summary": final.summary,
            "layers": final.layers,
            "viewport": final.viewport,
            "highlight_entities": [],
            "result_entities": final.result_entities,
            "filters": final.filters,
            "duration_ms": final.duration_ms,
            "provider": f"orchestrator/{final.provider}",
            "_orchestrator": {
                "sub_agent_count": len(sub_results),
                "successful_count": len([r for r in sub_results if r.success]),
            },
        })

    def _dispatch_parallel(
        self, sub_tasks: list[SubTask], deadline: float
    ) -> list[SubAgentResult]:
        """Run sub-agents in parallel via ThreadPoolExecutor."""
        if not sub_tasks:
            return []

        results = []

        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(sub_tasks))) as executor:
            futures = {}
            for task in sub_tasks:
                agent = SubAgent(
                    provider=self.provider,
                    sub_task=task,
                    ds=self.ds,
                    deadline=deadline,
                )
                future = executor.submit(agent.run)
                futures[future] = task

            for future in as_completed(futures, timeout=max(0, deadline - time.monotonic())):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    task = futures[future]
                    logger.warning(f"Sub-agent {task.intent} raised: {e}")
                    results.append(SubAgentResult(
                        sub_task_intent=task.intent,
                        summary="",
                        success=False,
                        error=str(e),
                    ))

        return results

    def _synthesize(
        self, query: str, sub_results: list[SubAgentResult], plan: QueryPlan
    ) -> OrchestratorResult:
        """Synthesize sub-agent results into a final response.

        If use_llm_synthesis is True, makes an LLM call for coherent synthesis.
        Falls back to deterministic concatenation on failure or when disabled.
        """
        successful = [r for r in sub_results if r.success and r.summary]
        all_findings = []
        all_entities = []

        for r in successful:
            all_findings.extend(r.key_findings)
            all_entities.extend(r.entity_references)

        # Try LLM synthesis
        if self.use_llm_synthesis and successful:
            summary = self._synthesize_with_llm(query, successful)
            if summary:
                return OrchestratorResult(
                    summary=summary,
                    sub_results=sub_results,
                    plan=plan,
                    result_entities=all_entities,
                    reasoning_steps=[
                        {"step": "plan", "domains": plan.domains_detected},
                        {"step": "dispatch", "agents": len(sub_results)},
                        {"step": "synthesize", "method": "llm", "successful": len(successful)},
                    ],
                )

        # Deterministic fallback
        if successful:
            summary = " | ".join(r.summary for r in successful)
        else:
            summary = "Unable to complete analysis — all sub-agents failed."

        return OrchestratorResult(
            summary=summary,
            sub_results=sub_results,
            plan=plan,
            result_entities=all_entities,
            reasoning_steps=[
                {"step": "plan", "domains": plan.domains_detected},
                {"step": "dispatch", "agents": len(sub_results)},
                {"step": "synthesize", "method": "concat", "successful": len(successful)},
            ],
        )

    def _synthesize_with_llm(
        self, query: str, successful_results: list[SubAgentResult]
    ) -> str | None:
        """Use an LLM call to synthesize sub-agent findings into a coherent response."""
        findings_block = ""
        for r in successful_results:
            findings_block += f"\n## {r.sub_task_intent}\n"
            findings_block += f"Summary: {r.summary}\n"
            if r.key_findings:
                findings_block += "Key findings:\n"
                for f in r.key_findings:
                    findings_block += f"- {f}\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an intelligence analyst synthesizing findings from "
                    "multiple domain specialists. Produce a coherent, concise summary "
                    "that answers the user's question. Respond with JSON:\n"
                    '{"summary": "...", "risk_level": 1-10, "key_findings": ["..."]}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original question: {query}\n\n"
                    f"Sub-agent findings:\n{findings_block}"
                ),
            },
        ]

        try:
            result = call_llm_simple(
                provider=self.provider,
                messages=messages,
                max_tokens=2048,
            )

            if result["error"]:
                logger.warning(f"Synthesis LLM failed: {result['error']}")
                return None

            content = result["content"]
            if not content:
                return None

            # Try to parse JSON
            try:
                parsed = json.loads(content)
                return parsed.get("summary", content)
            except json.JSONDecodeError:
                # Use raw content as summary
                return content

        except Exception as e:
            logger.warning(f"Synthesis failed: {e}")
            return None
