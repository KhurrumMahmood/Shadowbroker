"""ArtifactAgent — generates self-contained HTML visualizations from analysis data.

The agent receives a query, sub-agent findings summary, and optional structured data,
then generates an interactive HTML artifact using the ShadowBroker design tokens.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass

from services.agent.llm import call_llm_simple

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert data visualization engineer for ShadowBroker, a military-styled \
OSINT intelligence dashboard. Generate a SINGLE self-contained HTML file that \
visualizes the analysis data provided.

DESIGN REQUIREMENTS (ShadowBroker aesthetic):
- Dark background: #000000 (primary), rgb(5,5,8) (cards)
- Primary accent: cyan (#22d3ee / var(--sb-text-secondary))
- Text: rgb(243,244,246) (primary), monospace font at 10-12px
- Wide letter-spacing (0.1em-0.2em) on headings, uppercase labels
- Semi-transparent panels with subtle borders (rgba(8,145,178,0.4))
- Use CSS classes: sb-card, sb-heading, sb-label, sb-value, sb-badge-critical/elevated/normal
- Domain colors: aviation=#22d3ee, military=#facc15, maritime=#60a5fa, seismic=#fbbf24, \
fire=#f87171, infrastructure=#a78bfa, intelligence=#4ade80, markets=#34d399

TECHNICAL REQUIREMENTS:
- Self-contained HTML (no external dependencies except CDN scripts)
- For charts use Chart.js via CDN: <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
- For complex viz use D3.js via CDN: <script src="https://d3js.org/d3.v7.min.js"></script>
- Responsive layout that works in a panel (min 300px wide) and fullscreen
- All data must be embedded inline (no fetch calls)
- The HTML will have ShadowBroker CSS tokens injected (--sb-* variables)

OUTPUT: Return ONLY the HTML inside a ```html code block. No explanation text outside the block.
"""


@dataclass
class ArtifactAgentResult:
    """Result from artifact generation."""
    html: str
    title: str
    success: bool = True
    error: str | None = None
    artifact_type: str = ""
    duration_ms: int = 0
    reuse_artifact: str | None = None  # Set when agent decides to reuse an existing artifact
    suggested_tags: list[str] | None = None


class ArtifactAgent:
    """Generates HTML artifact visualizations from analysis data."""

    def __init__(
        self,
        provider: dict,
        query: str,
        sub_results_summary: str,
        data_context: dict | None = None,
        deadline: float = 0.0,
        registry=None,
        enhance_artifact: str | None = None,
    ):
        self.provider = provider
        self.query = query
        self.sub_results_summary = sub_results_summary
        self.data_context = data_context or {}
        self.deadline = deadline or (time.monotonic() + 30.0)
        self.registry = registry
        self.enhance_artifact = enhance_artifact

    def run(self) -> ArtifactAgentResult:
        start = time.monotonic()
        try:
            result = self._generate()
            result.duration_ms = int((time.monotonic() - start) * 1000)
            return result
        except Exception as e:
            logger.warning(f"ArtifactAgent failed: {e}")
            return ArtifactAgentResult(
                html="", title="", success=False, error=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    def _generate(self) -> ArtifactAgentResult:
        messages = self._build_messages()

        llm_result = call_llm_simple(
            provider=self.provider,
            messages=messages,
            deadline=self.deadline,
            max_tool_rounds=0,  # No tools — just generate HTML
            max_tokens=8192,
        )

        if llm_result["error"]:
            return ArtifactAgentResult(
                html="", title="", success=False, error=llm_result["error"],
            )

        content = llm_result["content"]

        # Check if the LLM decided to reuse an existing artifact
        reuse_name = self._check_reuse_decision(content)
        if reuse_name:
            return ArtifactAgentResult(
                html="", title="", success=True,
                reuse_artifact=reuse_name,
            )

        html = self._extract_html(content)
        title = self._generate_title()

        return ArtifactAgentResult(
            html=html,
            title=title,
            success=True,
            artifact_type=self._detect_type(),
        )

    def _build_messages(self) -> list[dict]:
        # Build system prompt with registry awareness
        system_content = _SYSTEM_PROMPT

        if self.registry:
            registry_summary = self.registry.get_registry_summary()
            system_content += f"""

ARTIFACT REGISTRY:
{registry_summary}

DECISION: Before generating new HTML, check if an existing artifact matches this query.
- If an existing artifact is a STRONG match, respond with ONLY this JSON (no code block):
  {{"action": "reuse", "artifact_name": "<name>"}}
- If you want to ENHANCE an existing artifact, generate the improved HTML.
- If nothing matches, generate new HTML as usual.
"""

        user_content = f"Query: {self.query}\n\nAnalysis findings:\n{self.sub_results_summary}"

        # Enhancement mode: include existing HTML
        if self.enhance_artifact and self.registry:
            result = self.registry.get_latest_version(self.enhance_artifact)
            if result:
                existing_html, meta = result
                user_content += (
                    f"\n\nENHANCEMENT MODE: Improve this existing artifact "
                    f"({self.enhance_artifact} v{meta['current_version']}).\n"
                    f"Existing HTML:\n```html\n{existing_html}\n```\n"
                    f"Keep the same structure but apply the requested changes."
                )

        if self.data_context:
            data_str = json.dumps(self.data_context, default=str)
            if len(data_str) > 4000:
                data_str = data_str[:4000] + "..."
            user_content += f"\n\nStructured data:\n{data_str}"

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _extract_html(self, content: str) -> str:
        """Extract HTML from LLM response, handling code blocks."""
        if not content:
            return ""

        # Try to extract from ```html ... ``` code block
        m = re.search(r"```html\s*\n?(.*?)```", content, re.DOTALL)
        if m:
            return m.group(1).strip()

        # Try generic code block
        m = re.search(r"```\s*\n?(.*?)```", content, re.DOTALL)
        if m:
            extracted = m.group(1).strip()
            if "<" in extracted:
                return extracted

        # If content looks like HTML, use it directly
        if content.strip().startswith("<!DOCTYPE") or content.strip().startswith("<html"):
            return content.strip()

        # Wrap plain text in basic HTML
        return f"<div class='sb-card'><p>{content}</p></div>"

    def _generate_title(self) -> str:
        """Generate a short title from the query."""
        q = self.query.strip()
        if len(q) > 50:
            q = q[:47] + "..."
        return q

    def _check_reuse_decision(self, content: str) -> str | None:
        """Check if the LLM decided to reuse an existing artifact."""
        content = content.strip()
        # Try to parse as JSON reuse decision
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and parsed.get("action") == "reuse":
                name = parsed.get("artifact_name", "")
                if name and self.registry:
                    # Verify the artifact actually exists
                    if self.registry.get_latest_version(name) is not None:
                        return name
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _detect_type(self) -> str:
        """Detect artifact type from query keywords."""
        q = self.query.lower()
        if any(w in q for w in ["chart", "graph", "plot", "trend"]):
            return "chart"
        if any(w in q for w in ["dashboard", "overview", "summary"]):
            return "dashboard"
        if any(w in q for w in ["timeline", "history", "sequence"]):
            return "timeline"
        if any(w in q for w in ["compare", "versus", "vs"]):
            return "comparison"
        return "analysis"
