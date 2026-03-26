"""Tests for the persistent artifact registry — CRUD, tag search, versioning."""
import json
import os
import tempfile
import pytest
from pathlib import Path

from services.agent.artifact_registry import ArtifactRegistry


@pytest.fixture
def registry_dir():
    """Create a temp directory with an empty registry."""
    with tempfile.TemporaryDirectory() as tmp:
        reg_path = Path(tmp) / "registry.json"
        reg_path.write_text(json.dumps({"artifacts": []}))
        yield Path(tmp)


@pytest.fixture
def registry(registry_dir):
    return ArtifactRegistry(registry_dir)


class TestRegistryCRUD:
    def test_save_new_artifact(self, registry, registry_dir):
        registry.save_artifact(
            name="maritime-map",
            title="Maritime Chokepoint Map",
            description="Ship positions near a chokepoint",
            tags=["maritime", "ships", "chokepoint", "map"],
            data_signature="ships + chokepoint_name",
            html="<div>map</div>",
            note="Initial version",
            created_by_admin=True,
        )
        # Directory created
        assert (registry_dir / "maritime-map").is_dir()
        # meta.json exists
        meta = json.loads((registry_dir / "maritime-map" / "meta.json").read_text())
        assert meta["name"] == "maritime-map"
        assert meta["current_version"] == 1
        assert meta["created_by_admin"] is True
        assert "maritime" in meta["tags"]
        # HTML saved
        assert (registry_dir / "maritime-map" / "v1.html").exists()
        # Registry updated
        reg = json.loads((registry_dir / "registry.json").read_text())
        assert len(reg["artifacts"]) == 1
        assert reg["artifacts"][0]["name"] == "maritime-map"

    def test_get_latest_version(self, registry):
        registry.save_artifact(
            name="test-viz", title="T", description="d",
            tags=["test"], data_signature="x",
            html="<div>v1</div>", note="v1",
        )
        html, meta = registry.get_latest_version("test-viz")
        assert html == "<div>v1</div>"
        assert meta["current_version"] == 1

    def test_get_missing_returns_none(self, registry):
        result = registry.get_latest_version("nonexistent")
        assert result is None

    def test_list_all(self, registry):
        registry.save_artifact(
            name="a1", title="A1", description="d",
            tags=["x"], data_signature="x", html="<div/>", note="init",
        )
        registry.save_artifact(
            name="a2", title="A2", description="d",
            tags=["y"], data_signature="y", html="<div/>", note="init",
        )
        entries = registry.list_all()
        assert len(entries) == 2
        names = {e["name"] for e in entries}
        assert names == {"a1", "a2"}


class TestVersioning:
    def test_create_version_increments(self, registry, registry_dir):
        registry.save_artifact(
            name="viz", title="Viz", description="d",
            tags=["test"], data_signature="x",
            html="<div>v1</div>", note="initial",
        )
        registry.create_version("viz", "<div>v2</div>", "added filters")
        html, meta = registry.get_latest_version("viz")
        assert html == "<div>v2</div>"
        assert meta["current_version"] == 2
        assert len(meta["versions"]) == 2
        assert meta["versions"][-1]["note"] == "added filters"

    def test_create_version_preserves_old(self, registry, registry_dir):
        registry.save_artifact(
            name="viz", title="Viz", description="d",
            tags=["test"], data_signature="x",
            html="<div>v1</div>", note="initial",
        )
        registry.create_version("viz", "<div>v2</div>", "v2")
        # v1 still on disk
        assert (registry_dir / "viz" / "v1.html").read_text() == "<div>v1</div>"
        assert (registry_dir / "viz" / "v2.html").read_text() == "<div>v2</div>"

    def test_create_version_on_missing_raises(self, registry):
        with pytest.raises(ValueError, match="not found"):
            registry.create_version("nonexistent", "<div/>", "note")

    def test_get_specific_version(self, registry):
        registry.save_artifact(
            name="viz", title="Viz", description="d",
            tags=["test"], data_signature="x",
            html="<div>v1</div>", note="initial",
        )
        registry.create_version("viz", "<div>v2</div>", "v2")
        registry.create_version("viz", "<div>v3</div>", "v3")
        html = registry.get_version("viz", 1)
        assert html == "<div>v1</div>"
        html = registry.get_version("viz", 2)
        assert html == "<div>v2</div>"
        html = registry.get_version("viz", 3)
        assert html == "<div>v3</div>"

    def test_registry_json_updated_on_version(self, registry, registry_dir):
        registry.save_artifact(
            name="viz", title="Viz", description="d",
            tags=["test"], data_signature="x",
            html="<div>v1</div>", note="initial",
        )
        registry.create_version("viz", "<div>v2</div>", "v2")
        reg = json.loads((registry_dir / "registry.json").read_text())
        entry = reg["artifacts"][0]
        assert entry["current_version"] == 2


class TestTagSearch:
    def test_exact_tag_match(self, registry):
        registry.save_artifact(
            name="ship-map", title="Ship Map", description="d",
            tags=["maritime", "ships", "map"], data_signature="ships",
            html="<div/>", note="init",
        )
        registry.save_artifact(
            name="flight-map", title="Flight Map", description="d",
            tags=["aviation", "flights", "map"], data_signature="flights",
            html="<div/>", note="init",
        )
        results = registry.search(["maritime", "ships"])
        assert len(results) >= 1
        assert results[0]["name"] == "ship-map"

    def test_partial_tag_match(self, registry):
        registry.save_artifact(
            name="ship-map", title="Ship Map", description="d",
            tags=["maritime", "ships", "map", "chokepoint"], data_signature="ships",
            html="<div/>", note="init",
        )
        results = registry.search(["map"])
        assert len(results) >= 1

    def test_no_match_returns_empty(self, registry):
        registry.save_artifact(
            name="ship-map", title="Ship Map", description="d",
            tags=["maritime", "ships"], data_signature="ships",
            html="<div/>", note="init",
        )
        results = registry.search(["nuclear", "weapons"])
        assert len(results) == 0

    def test_results_ranked_by_match_count(self, registry):
        registry.save_artifact(
            name="broad", title="Broad", description="d",
            tags=["maritime", "map"], data_signature="x",
            html="<div/>", note="init",
        )
        registry.save_artifact(
            name="specific", title="Specific", description="d",
            tags=["maritime", "ships", "chokepoint", "map"], data_signature="x",
            html="<div/>", note="init",
        )
        results = registry.search(["maritime", "ships", "chokepoint"])
        assert results[0]["name"] == "specific"  # 3 matches
        assert results[1]["name"] == "broad"  # 1 match

    def test_search_case_insensitive(self, registry):
        registry.save_artifact(
            name="ship-map", title="Ship Map", description="d",
            tags=["Maritime", "Ships"], data_signature="ships",
            html="<div/>", note="init",
        )
        results = registry.search(["maritime", "ships"])
        assert len(results) >= 1


class TestAdminFlag:
    def test_admin_flag_preserved(self, registry):
        registry.save_artifact(
            name="admin-viz", title="Admin Viz", description="d",
            tags=["test"], data_signature="x",
            html="<div/>", note="init", created_by_admin=True,
        )
        _, meta = registry.get_latest_version("admin-viz")
        assert meta["created_by_admin"] is True

    def test_non_admin_default(self, registry):
        registry.save_artifact(
            name="user-viz", title="User Viz", description="d",
            tags=["test"], data_signature="x",
            html="<div/>", note="init",
        )
        _, meta = registry.get_latest_version("user-viz")
        assert meta["created_by_admin"] is False


class TestRegistryReload:
    def test_survives_reload(self, registry_dir):
        """Registry data persists across instances."""
        reg1 = ArtifactRegistry(registry_dir)
        reg1.save_artifact(
            name="persist", title="P", description="d",
            tags=["test"], data_signature="x",
            html="<div>persistent</div>", note="init",
        )
        # Create a new instance pointing at same directory
        reg2 = ArtifactRegistry(registry_dir)
        html, meta = reg2.get_latest_version("persist")
        assert html == "<div>persistent</div>"
        assert meta["name"] == "persist"
