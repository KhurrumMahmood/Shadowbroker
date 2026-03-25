"""Eval framework for the agent system.

Scores agent responses against scenario expectations. Designed for:
1. Deterministic testing with StaticDataSource (no LLM needed for scoring)
2. LLM-based evaluation when testing real agent responses
3. METRIC output compatible with autoresearch optimization loops
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalResult:
    """Result of evaluating a single agent response against expectations."""
    scenario: str
    query: str
    score: float = 0.0           # 0-1 composite
    mentions_score: float = 0.0  # Did it mention required things?
    sources_score: float = 0.0   # Did it query the right data sources?
    judgment_score: float = 0.0  # Was the risk level reasonable?
    entity_score: float = 0.0    # Did it include the right entity types?
    latency: float = 0.0         # Seconds
    llm_calls: int = 0
    tools_called: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def compute_composite(self) -> float:
        """Weighted composite score. Higher weight on mentions + sources."""
        self.score = (
            self.mentions_score * 0.35
            + self.sources_score * 0.30
            + self.judgment_score * 0.20
            + self.entity_score * 0.15
        )
        return self.score


def score_mentions(response_text: str, required_mentions: list[str]) -> float:
    """Score how many required terms appear in the response text (case-insensitive).

    Returns fraction of required mentions found (0.0 to 1.0).
    """
    if not required_mentions:
        return 1.0
    text_lower = response_text.lower()
    found = sum(1 for m in required_mentions if m.lower() in text_lower)
    return found / len(required_mentions)


def score_sources(
    queried_categories: list[str],
    required_categories: list[str],
) -> float:
    """Score whether the agent queried the right data sources.

    Returns fraction of required categories that were queried (0.0 to 1.0).
    """
    if not required_categories:
        return 1.0
    queried_set = set(queried_categories)
    found = sum(1 for c in required_categories if c in queried_set)
    return found / len(required_categories)


def score_judgment(risk_level: float | None, expected_range: list[int]) -> float:
    """Score whether the agent's risk assessment falls in the expected range.

    Returns 1.0 if within range, 0.5 if within 2 points, 0.0 if far off.
    Returns 1.0 if risk_level is None (not assessed) and range allows low values.
    """
    if risk_level is None:
        # If the expected range includes 0, not assessing risk is acceptable
        return 1.0 if expected_range[0] <= 1 else 0.0
    low, high = expected_range
    if low <= risk_level <= high:
        return 1.0
    # Partial credit for being close
    distance = min(abs(risk_level - low), abs(risk_level - high))
    if distance <= 2:
        return 0.5
    return 0.0


def score_entities(
    returned_entity_types: list[str],
    required_entity_types: list[str],
) -> float:
    """Score whether the agent returned the right entity types.

    Returns fraction of required entity types present (0.0 to 1.0).
    """
    if not required_entity_types:
        return 1.0
    returned_set = set(returned_entity_types)
    found = sum(1 for t in required_entity_types if t in returned_set)
    return found / len(required_entity_types)


@dataclass
class AgentResponse:
    """Simplified representation of an agent response for evaluation."""
    summary: str = ""
    risk_level: float | None = None
    queried_categories: list[str] = field(default_factory=list)
    returned_entity_types: list[str] = field(default_factory=list)
    latency: float = 0.0
    llm_calls: int = 0
    tools_called: list[str] = field(default_factory=list)


def evaluate(
    scenario: str,
    query: str,
    response: AgentResponse,
    expected: dict,
) -> EvalResult:
    """Evaluate an agent response against expected assertions.

    Args:
        scenario: Scenario name (e.g. "hormuz_crisis")
        query: The user query
        response: The agent's response
        expected: Dict from expected.json test_queries entry with keys:
            required_mentions, required_data_sources_queried,
            risk_level_range, must_include_entity_types, max_latency_seconds
    """
    result = EvalResult(scenario=scenario, query=query)

    result.mentions_score = score_mentions(
        response.summary,
        expected.get("required_mentions", []),
    )
    result.sources_score = score_sources(
        response.queried_categories,
        expected.get("required_data_sources_queried", []),
    )
    result.judgment_score = score_judgment(
        response.risk_level,
        expected.get("risk_level_range", [0, 10]),
    )
    result.entity_score = score_entities(
        response.returned_entity_types,
        expected.get("must_include_entity_types", []),
    )
    result.latency = response.latency
    result.llm_calls = response.llm_calls
    result.tools_called = response.tools_called

    # Latency penalty: deduct from composite if over budget
    max_latency = expected.get("max_latency_seconds", 10.0)
    result.details["latency_ok"] = response.latency <= max_latency

    result.compute_composite()
    return result


def format_eval_report(results: list[EvalResult]) -> str:
    """Format eval results as a human-readable table."""
    if not results:
        return "No eval results."

    lines = [
        f"{'SCENARIO':<25} {'QUERY':<50} {'SCORE':>6} "
        f"{'MENT':>6} {'SRC':>6} {'JUDG':>6} {'ENT':>6} {'LAT':>7}",
        "-" * 115,
    ]

    for r in results:
        query_short = r.query[:47] + "..." if len(r.query) > 50 else r.query
        lines.append(
            f"{r.scenario:<25} {query_short:<50} {r.score:>6.2f} "
            f"{r.mentions_score:>6.2f} {r.sources_score:>6.2f} "
            f"{r.judgment_score:>6.2f} {r.entity_score:>6.2f} "
            f"{r.latency:>6.1f}s"
        )

    overall = sum(r.score for r in results) / len(results) if results else 0
    lines.append("-" * 115)
    lines.append(f"{'OVERALL':<25} {'':50} {overall:>6.2f}")

    # METRIC line for autoresearch compatibility
    lines.append("")
    lines.append(f"METRIC overall_eval_score={overall:.4f}")

    return "\n".join(lines)
