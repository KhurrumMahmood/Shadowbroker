"""Persistent artifact registry — filesystem-backed with tag search and versioning.

Artifacts live in named directories under a registry root:
  registry_root/
    registry.json          # Master index
    maritime-map/
      meta.json            # Tags, versions, data signature
      v1.html              # Version 1 HTML
      v2.html              # Version 2 HTML
      mock-data.json       # Test data (optional)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
import re
from threading import Lock

logger = logging.getLogger(__name__)


class ArtifactRegistry:
    """Filesystem-backed artifact registry with tag search and versioning."""

    _NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")

    def __init__(self, registry_root: Path):
        self._root = Path(registry_root)
        self._registry_path = self._root / "registry.json"
        self._lock = Lock()

    @classmethod
    def _validate_name(cls, name: str) -> None:
        """Validate artifact name to prevent path traversal and filesystem issues."""
        if not name or not cls._NAME_PATTERN.match(name):
            raise ValueError(
                f"Invalid artifact name '{name}': must be 1-80 lowercase alphanumeric chars or hyphens, "
                "starting with alphanumeric"
            )

    def _read_registry(self) -> dict:
        if not self._registry_path.exists():
            return {"artifacts": []}
        return json.loads(self._registry_path.read_text())

    def _write_registry(self, data: dict) -> None:
        self._registry_path.write_text(json.dumps(data, indent=2))

    def _read_meta(self, name: str) -> dict | None:
        self._validate_name(name)
        meta_path = self._root / name / "meta.json"
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text())

    def _write_meta(self, name: str, meta: dict) -> None:
        self._validate_name(name)
        meta_path = self._root / name / "meta.json"
        meta_path.write_text(json.dumps(meta, indent=2))

    def save_artifact(
        self,
        name: str,
        title: str,
        description: str,
        tags: list[str],
        data_signature: str,
        html: str,
        note: str,
        created_by_admin: bool = False,
        accepts_data: dict | None = None,
    ) -> None:
        """Save a new artifact (creates directory, meta.json, v1.html, registry entry)."""
        self._validate_name(name)
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            # Create directory
            art_dir = self._root / name
            art_dir.mkdir(parents=True, exist_ok=True)

            # Write HTML as v1
            (art_dir / "v1.html").write_text(html)

            # Write meta.json
            meta = {
                "name": name,
                "title": title,
                "tags": tags,
                "data_signature": data_signature,
                "versions": [
                    {"version": 1, "note": note, "created_at": now},
                ],
                "current_version": 1,
                "created_by_admin": created_by_admin,
                "accepts_data": accepts_data or {},
            }
            self._write_meta(name, meta)

            # Update registry.json
            reg = self._read_registry()
            # Remove existing entry if any
            reg["artifacts"] = [e for e in reg["artifacts"] if e["name"] != name]
            reg["artifacts"].append({
                "name": name,
                "title": title,
                "description": description,
                "tags": tags,
                "data_signature": data_signature,
                "current_version": 1,
                "type": "html",
                "created_by_admin": created_by_admin,
                "created_at": now,
                "updated_at": now,
            })
            self._write_registry(reg)

    def create_version(self, name: str, html: str, note: str) -> int:
        """Append a new version to an existing artifact. Returns the new version number."""
        self._validate_name(name)
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            meta = self._read_meta(name)
            if meta is None:
                raise ValueError(f"Artifact '{name}' not found in registry")

            new_version = meta["current_version"] + 1
            meta["versions"].append({
                "version": new_version,
                "note": note,
                "created_at": now,
            })
            meta["current_version"] = new_version
            self._write_meta(name, meta)

            # Write HTML
            (self._root / name / f"v{new_version}.html").write_text(html)

            # Update registry.json
            reg = self._read_registry()
            for entry in reg["artifacts"]:
                if entry["name"] == name:
                    entry["current_version"] = new_version
                    entry["updated_at"] = now
                    break
            self._write_registry(reg)

        return new_version

    def get_latest_version(self, name: str) -> tuple[str, dict] | None:
        """Get the latest HTML and meta for an artifact. Returns None if not found."""
        meta = self._read_meta(name)
        if meta is None:
            return None
        v = meta["current_version"]
        html_path = self._root / name / f"v{v}.html"
        if not html_path.exists():
            return None
        return html_path.read_text(), meta

    def get_version(self, name: str, version: int) -> str | None:
        """Get a specific version's HTML. Returns None if not found."""
        self._validate_name(name)
        html_path = self._root / name / f"v{version}.html"
        if not html_path.exists():
            return None
        return html_path.read_text()

    def search(self, tags: list[str], min_score: int = 1) -> list[dict]:
        """Search artifacts by tags. Returns registry entries ranked by match count."""
        reg = self._read_registry()
        query_tags = {t.lower() for t in tags}

        scored = []
        for entry in reg["artifacts"]:
            entry_tags = {t.lower() for t in entry.get("tags", [])}
            overlap = len(query_tags & entry_tags)
            if overlap >= min_score:
                scored.append((overlap, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored]

    def list_all(self) -> list[dict]:
        """List all artifacts in the registry."""
        return self._read_registry().get("artifacts", [])

    def get_registry_summary(self) -> str:
        """Return a concise text summary for inclusion in LLM prompts."""
        entries = self.list_all()
        if not entries:
            return "No saved artifacts in registry."
        lines = []
        for e in entries:
            tags_str = ", ".join(e["tags"][:6])
            lines.append(
                f"- {e['name']} (v{e['current_version']}, {e['type']}): "
                f"{e['description']} [{tags_str}]"
            )
        return "Saved artifacts:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Tag extraction from natural language queries
# ---------------------------------------------------------------------------
_DOMAIN_KEYWORDS = {
    "maritime": ["ship", "ships", "vessel", "vessels", "tanker", "cargo", "ais", "maritime", "port"],
    "aviation": ["flight", "flights", "aircraft", "plane", "planes", "aviation", "airline"],
    "military": ["military", "mil", "fighter", "bomber", "surveillance", "isr", "navy", "airforce"],
    "seismic": ["earthquake", "earthquakes", "seismic", "magnitude", "quake"],
    "fire": ["fire", "fires", "hotspot", "hotspots", "wildfire", "firms"],
    "infrastructure": ["internet", "outage", "outages", "power", "infrastructure", "cable"],
    "intelligence": ["gdelt", "conflict", "event", "events", "intelligence", "osint"],
    "markets": ["oil", "stock", "stocks", "market", "commodity", "price"],
}

_VIZ_KEYWORDS = {
    "map": ["map", "location", "where", "near", "positions", "overlay"],
    "chart": ["chart", "graph", "plot", "trend", "over time"],
    "timeline": ["timeline", "history", "sequence", "temporal", "when"],
    "dashboard": ["dashboard", "overview", "summary", "status"],
    "compare": ["compare", "comparison", "versus", "vs", "difference"],
    "table": ["table", "list", "breakdown", "detail"],
}

_LOCATION_KEYWORDS = [
    "hormuz", "suez", "malacca", "taiwan", "bab-el-mandeb", "panama",
    "south china sea", "black sea", "baltic", "mediterranean", "red sea",
    "gulf", "persian", "atlantic", "pacific", "indian ocean", "arctic",
]


def extract_tags_from_query(query: str) -> list[str]:
    """Extract searchable tags from a natural language query."""
    q = query.lower()
    tags = []

    # Domain tags
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            tags.append(domain)
            # Also add the specific matching keyword
            for kw in keywords:
                if kw in q and kw != domain:
                    tags.append(kw)

    # Viz type tags
    for viz_type, keywords in _VIZ_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            tags.append(viz_type)

    # Location tags
    for loc in _LOCATION_KEYWORDS:
        if loc in q:
            tags.append(loc)

    # Chokepoint detection
    if any(w in q for w in ["strait", "chokepoint", "channel", "canal"]):
        tags.append("chokepoint")

    # Convergence / proximity
    if any(w in q for w in ["convergence", "converging", "proximity", "near"]):
        tags.append("convergence")

    return list(dict.fromkeys(tags))  # Deduplicate while preserving order


# Global singleton
_registry: ArtifactRegistry | None = None


def get_artifact_registry() -> ArtifactRegistry:
    """Get the global artifact registry. Points to frontend/src/artifacts/ by default."""
    global _registry
    if _registry is None:
        # Resolve path relative to backend directory
        backend_dir = Path(__file__).parent.parent.parent
        artifacts_dir = backend_dir.parent / "frontend" / "src" / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        if not (artifacts_dir / "registry.json").exists():
            (artifacts_dir / "registry.json").write_text(json.dumps({"artifacts": []}))
        _registry = ArtifactRegistry(artifacts_dir)
    return _registry
