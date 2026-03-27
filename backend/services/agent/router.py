"""Deterministic query complexity classifier.

Pure keyword matching — no LLM call. Microsecond latency.
Classifies queries as SIMPLE (single-domain) or COMPOUND (multi-domain/analytical).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class QueryComplexity(Enum):
    SIMPLE = "simple"
    COMPOUND = "compound"


@dataclass
class SubTask:
    """A decomposed piece of a compound query."""
    intent: str              # e.g. "spatial_maritime", "temporal_aviation"
    query_fragment: str      # relevant part of original query
    tool_hints: list[str] = field(default_factory=list)


@dataclass
class QueryPlan:
    """Result of query classification."""
    complexity: QueryComplexity
    original_query: str
    sub_tasks: list[SubTask] = field(default_factory=list)
    domains_detected: list[str] = field(default_factory=list)


# ── Domain taxonomy ──────────────────────────────────────────────────

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "maritime": [
        "ship", "vessel", "tanker", "cargo", "port", "naval", "strait",
        "ais", "maritime", "fleet", "carrier", "destroyer", "frigate",
        "yacht", "maritime", "mmsi", "shipping",
    ],
    "aviation": [
        "military flight", "military aircraft",
        "flight", "aircraft", "plane", "jet", "c-17", "c-5", "airspace",
        "callsign", "airlift", "helicopter", "drone", "uav", "airborne",
        "flying", "p-8", "mq-9", "f-35", "f-16", "bomber",
    ],
    "seismic": [
        "earthquake", "quake", "seismic", "tremor", "magnitude", "richter",
        "aftershock", "tectonic",
    ],
    "infrastructure": [
        "power plant", "datacenter", "internet outage", "grid", "cable",
        "infrastructure", "pipeline", "refinery", "energy",
        "train", "rail", "amtrak", "railway",
    ],
    "conflict": [
        "military base", "military posture", "military deployment",
        "conflict", "war", "tension", "crisis", "deployment",
        "troops", "posture", "defense", "defence", "combat",
        "hostile", "aggression",
        "ukraine alert", "air raid", "artillery", "ukraine",
    ],
    "economic": [
        "oil", "stock", "price", "market", "trade", "sanctions",
        "economic", "financial", "commodity",
        "prediction market", "polymarket", "kalshi", "odds", "probability",
        "betting", "forecast",
    ],
    "intelligence": [
        "gps jamming", "ew", "electronic warfare", "surveillance", "recon",
        "intelligence", "sigint", "elint", "satellite", "spy",
        "meshtastic", "mesh network", "lora",
    ],
    "disinformation": [
        "fimi", "disinformation", "propaganda", "influence operation",
        "fake news", "information warfare", "euvsdisinfo", "narrative",
        "foreign interference", "manipulation",
    ],
}

# Compile domain patterns (word boundary matching for short terms)
_DOMAIN_PATTERNS: dict[str, re.Pattern] = {}
for _domain, _keywords in _DOMAIN_KEYWORDS.items():
    # Sort by length descending so multi-word phrases match first
    sorted_kw = sorted(_keywords, key=len, reverse=True)
    pattern = "|".join(re.escape(kw) for kw in sorted_kw)
    _DOMAIN_PATTERNS[_domain] = re.compile(pattern, re.IGNORECASE)

# Cross-correlation / analytical keywords → always compound
_COMPOUND_KEYWORDS = re.compile(
    r"\b(?:"
    r"cascad(?:e|ing)|compound|connected|correlat(?:e|ion|ed|ing)"
    r"|compar(?:e|ing|ison)|versus|vs\.?"
    r"|risk assessment|impact"
    r"|unusual|anomal(?:y|ous|ies)|developing"
    r"|geopolitical|what.{0,5}unusual|what.{0,10}should.{0,5}know"
    r"|what.{0,5}changed"
    r")\b",
    re.IGNORECASE,
)

# Temporal keywords
_TEMPORAL_KEYWORDS = re.compile(
    r"\b(?:changed|hours? ago|last \d+|since|trend|historical|compared? to)\b",
    re.IGNORECASE,
)

# Domain-to-tool hints
_DOMAIN_TOOL_HINTS: dict[str, list[str]] = {
    "maritime": ["query_data", "proximity_search", "pattern_detect"],
    "aviation": ["query_data", "corridor_analysis", "proximity_search"],
    "seismic": ["query_data", "proximity_search", "cross_correlate"],
    "infrastructure": ["query_data", "proximity_search", "cross_correlate"],
    "conflict": ["query_data", "aggregate_data", "proximity_search"],
    "economic": ["web_search", "query_data"],
    "intelligence": ["query_data", "proximity_search", "anomaly_scan"],
    "disinformation": ["query_data", "web_search"],
}


class QueryRouter:
    """Deterministic query classifier — no LLM, microsecond latency."""

    def classify(self, query: str) -> QueryPlan:
        """Classify a query as simple or compound and detect domains."""
        domains = self._detect_domains(query)
        is_compound = self._is_compound(query, domains)

        if is_compound:
            sub_tasks = self._decompose(query, domains)
            return QueryPlan(
                complexity=QueryComplexity.COMPOUND,
                original_query=query,
                sub_tasks=sub_tasks,
                domains_detected=domains,
            )

        return QueryPlan(
            complexity=QueryComplexity.SIMPLE,
            original_query=query,
            sub_tasks=[],
            domains_detected=domains,
        )

    def _detect_domains(self, query: str) -> list[str]:
        """Detect which data domains a query touches."""
        found = []
        for domain, pattern in _DOMAIN_PATTERNS.items():
            if pattern.search(query):
                found.append(domain)
        return found

    def _is_compound(self, query: str, domains: list[str]) -> bool:
        """Determine if a query requires multi-agent orchestration."""
        # Explicit cross-correlation / analytical keywords
        if _COMPOUND_KEYWORDS.search(query):
            return True

        # Multi-domain (2+ distinct domains)
        if len(domains) >= 2:
            return True

        # Temporal + spatial combined
        if _TEMPORAL_KEYWORDS.search(query) and domains:
            return True

        return False

    def _decompose(self, query: str, domains: list[str]) -> list[SubTask]:
        """Break a compound query into sub-tasks."""
        sub_tasks = []

        # One sub-task per detected domain
        for domain in domains:
            hints = _DOMAIN_TOOL_HINTS.get(domain, ["query_data"])
            sub_tasks.append(SubTask(
                intent=f"analyze_{domain}",
                query_fragment=query,
                tool_hints=hints,
            ))

        # If temporal keywords present, add a temporal sub-task
        if _TEMPORAL_KEYWORDS.search(query):
            sub_tasks.append(SubTask(
                intent="temporal_analysis",
                query_fragment=query,
                tool_hints=["temporal_compare"],
            ))

        # If no domains but compound keywords triggered, add a discovery sub-task
        if not sub_tasks:
            sub_tasks.append(SubTask(
                intent="discovery",
                query_fragment=query,
                tool_hints=["anomaly_scan", "cross_correlate", "proximity_search"],
            ))

        # Always include a synthesis sub-task for compound queries
        if len(sub_tasks) >= 2:
            sub_tasks.append(SubTask(
                intent="synthesis",
                query_fragment=query,
                tool_hints=[],
            ))

        return sub_tasks
