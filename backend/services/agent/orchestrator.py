"""Orchestrator — dispatches sub-agents in parallel, collects and synthesizes results."""
from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from services.agent.llm import call_llm_simple
from services.agent.router import QueryPlan, SubTask
from services.agent.sub_agent import SubAgent, SubAgentResult
from services.agent.artifact_agent import ArtifactAgent
from services.agent.artifacts import get_artifact_store, Artifact
from services.agent.artifact_registry import get_artifact_registry, extract_tags_from_query

logger = logging.getLogger(__name__)

_MAX_WORKERS = 3
_AGENT_TIME_BUDGET_RATIO = 0.7  # 70% of total time for agents, 30% reserved
_SLUG_PATTERN = re.compile(r"[^a-z0-9-]")


def _sse(event: str, data: dict) -> str:
    """Format a single SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _make_error_result(task: SubTask, error: Exception) -> SubAgentResult:
    """Build a failed SubAgentResult from a task and its exception."""
    return SubAgentResult(
        sub_task_intent=task.intent,
        summary="",
        success=False,
        error=str(error),
    )


def _slugify(title: str) -> str:
    """Convert a title to a lowercase alphanumeric-and-hyphen slug (max 40 chars)."""
    raw = title.lower().replace(" ", "-")[:40] if title else "artifact"
    slug = _SLUG_PATTERN.sub("", raw).strip("-")
    return slug or "artifact"


@dataclass
class _ArtifactOutcome:
    """Result of artifact generation, replacing a fragile 4-tuple."""
    artifact_id: str | None = None
    title: str | None = None
    registry_name: str | None = None
    version: int | None = None

    @property
    def created(self) -> bool:
        return self.artifact_id is not None


_EMPTY_ARTIFACT = _ArtifactOutcome()


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
        generate_artifact: bool = False,
        enhance_artifact_name: str | None = None,
    ):
        self.provider = provider
        self.ds = ds
        self.total_budget = total_budget_seconds
        self.use_llm_synthesis = use_llm_synthesis
        self.generate_artifact = generate_artifact
        self.enhance_artifact_name = enhance_artifact_name

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
          - artifact: artifact generation (if enabled)
          - result: final synthesized result
        """
        start = time.monotonic()
        agent_deadline = start + (self.total_budget * _AGENT_TIME_BUDGET_RATIO)

        yield _sse("plan", {
            "complexity": plan.complexity.value,
            "sub_tasks": [
                {"intent": t.intent, "description": t.query_fragment}
                for t in plan.sub_tasks
            ],
        })

        # Collect SSE events from sub-agent completions to yield after dispatch
        pending_events: list[str] = []

        def _on_result(result: SubAgentResult) -> None:
            pending_events.append(_sse("sub_result", {
                "sub_task": result.sub_task_intent,
                "summary": result.summary,
                "success": result.success,
                "duration_ms": result.duration_ms,
            }))

        agent_tasks = [t for t in plan.sub_tasks if t.intent != "synthesis"]
        sub_results = self._dispatch_parallel(agent_tasks, agent_deadline, on_result=_on_result)

        yield from pending_events

        final = self._synthesize(query, sub_results, plan)
        final.duration_ms = int((time.monotonic() - start) * 1000)
        final.provider = self.provider.get("model", "")

        # Generate artifact if enabled and we have successful sub-results
        successful = [r for r in sub_results if r.success]
        artifact = _EMPTY_ARTIFACT
        if self.generate_artifact and successful:
            try:
                artifact = self._generate_artifact(query, successful, final.summary)
                if artifact.created:
                    art_event: dict = {
                        "artifact_id": artifact.artifact_id,
                        "title": artifact.title,
                    }
                    if artifact.registry_name:
                        art_event["registry_name"] = artifact.registry_name
                    if artifact.version is not None:
                        art_event["version"] = artifact.version
                    yield _sse("artifact", art_event)
            except Exception as e:
                logger.warning(f"Artifact generation failed: {e}")

        result_data: dict = {
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
                "successful_count": len(successful),
            },
        }
        if artifact.created:
            result_data["artifact_id"] = artifact.artifact_id
            result_data["artifact_title"] = artifact.title

        yield _sse("result", result_data)

    def _dispatch_parallel(
        self,
        sub_tasks: list[SubTask],
        deadline: float,
        on_result: Callable[[SubAgentResult], None] | None = None,
    ) -> list[SubAgentResult]:
        """Run sub-agents in parallel via ThreadPoolExecutor.

        If on_result is provided, it is called with each result as it completes
        (used by run_streaming to build SSE events incrementally).
        """
        if not sub_tasks:
            return []

        results: list[SubAgentResult] = []

        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(sub_tasks))) as executor:
            futures = {}
            for task in sub_tasks:
                agent = SubAgent(
                    provider=self.provider,
                    sub_task=task,
                    ds=self.ds,
                    deadline=deadline,
                )
                futures[executor.submit(agent.run)] = task

            try:
                for future in as_completed(futures, timeout=max(0, deadline - time.monotonic())):
                    try:
                        result = future.result()
                    except Exception as e:
                        task = futures[future]
                        logger.warning(f"Sub-agent {task.intent} raised: {e}")
                        result = _make_error_result(task, e)
                    results.append(result)
                    if on_result:
                        on_result(result)
            except TimeoutError:
                logger.warning(
                    f"Orchestrator deadline hit — {len(results)}/{len(sub_tasks)} agents completed"
                )

        return results

    def _synthesize(
        self, query: str, sub_results: list[SubAgentResult], plan: QueryPlan
    ) -> OrchestratorResult:
        """Synthesize sub-agent results into a final response.

        If use_llm_synthesis is True, makes an LLM call for coherent synthesis.
        Falls back to deterministic concatenation on failure or when disabled.
        """
        successful = [r for r in sub_results if r.success and r.summary]
        all_entities = [ref for r in successful for ref in r.entity_references]

        # Try LLM synthesis, fall back to deterministic concatenation
        method = "concat"
        summary = None
        if self.use_llm_synthesis and successful:
            summary = self._synthesize_with_llm(query, successful)
            if summary:
                method = "llm"

        if not summary:
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
                {"step": "synthesize", "method": method, "successful": len(successful)},
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

    def _generate_artifact(
        self,
        query: str,
        successful: list[SubAgentResult],
        synthesis_summary: str,
    ) -> _ArtifactOutcome:
        """Generate an HTML artifact from sub-agent findings."""
        findings = "\n".join(
            f"[{r.sub_task_intent}] {r.summary}" for r in successful
        )
        data_context = {
            "entities": [
                ref for r in successful for ref in r.entity_references
            ][:20],
        }

        registry = get_artifact_registry()
        query_tags = extract_tags_from_query(query)

        agent = ArtifactAgent(
            provider=self.provider,
            query=query,
            sub_results_summary=f"{synthesis_summary}\n\nDetails:\n{findings}",
            data_context=data_context,
            deadline=time.monotonic() + 15.0,
            registry=registry,
            enhance_artifact=self.enhance_artifact_name,
        )
        result = agent.run()

        if not result.success:
            logger.warning(f"Artifact generation failed: {result.error}")
            return _EMPTY_ARTIFACT

        # Agent decided to reuse an existing artifact (skip reuse when enhancing)
        if result.reuse_artifact and not self.enhance_artifact_name:
            existing = registry.get_latest_version(result.reuse_artifact)
            if existing:
                html, meta = existing
                store = get_artifact_store()
                artifact = Artifact(
                    html=html, title=meta["title"],
                    query=query, artifact_type="reused",
                )
                artifact_id = store.save(artifact)
                logger.info(f"Artifact reused: {result.reuse_artifact} → {artifact_id}")
                return _ArtifactOutcome(
                    artifact_id=artifact_id,
                    title=meta["title"],
                    registry_name=result.reuse_artifact,
                    version=meta.get("current_version"),
                )

        if not result.html:
            return _EMPTY_ARTIFACT

        # Save to ephemeral store for immediate serving
        store = get_artifact_store()
        artifact = Artifact(
            html=result.html, title=result.title,
            query=query, artifact_type=result.artifact_type,
        )
        artifact_id = store.save(artifact)

        # Enhancement path: create new version of existing artifact
        if self.enhance_artifact_name:
            try:
                version = registry.create_version(
                    name=self.enhance_artifact_name,
                    html=result.html,
                    note=f"Enhanced for: {query[:80]}",
                )
                logger.info(f"Artifact enhanced: {self.enhance_artifact_name} → v{version}")
                return _ArtifactOutcome(
                    artifact_id=artifact_id,
                    title=result.title,
                    registry_name=self.enhance_artifact_name,
                    version=version,
                )
            except Exception as e:
                logger.warning(f"Version creation failed, falling back to new artifact: {e}")

        # New artifact path: persist to the registry for future reuse
        slug = _slugify(result.title)
        registry_name = None
        version = None
        try:
            registry.save_artifact(
                name=slug,
                title=result.title,
                description=f"Auto-generated from: {query[:100]}",
                tags=query_tags,
                data_signature=result.artifact_type,
                html=result.html,
                note=f"Generated for query: {query[:80]}",
            )
            registry_name = slug
            version = 1
            logger.info(f"Artifact persisted to registry: {slug}")
        except Exception as e:
            logger.debug(f"Registry save skipped: {e}")

        logger.info(f"Artifact generated: {artifact_id} ({result.artifact_type})")
        return _ArtifactOutcome(
            artifact_id=artifact_id,
            title=result.title,
            registry_name=registry_name,
            version=version,
        )
