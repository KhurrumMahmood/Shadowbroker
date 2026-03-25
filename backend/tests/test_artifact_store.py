"""Tests for artifact storage and serving."""
import time
import pytest
from services.agent.artifacts import ArtifactStore, Artifact


class TestArtifactStore:
    def setup_method(self):
        self.store = ArtifactStore(max_artifacts=10, ttl_seconds=60)

    def test_save_and_get(self):
        art = Artifact(html="<h1>Test</h1>", title="Test Artifact", query="test query")
        aid = self.store.save(art)
        assert aid  # non-empty string
        retrieved = self.store.get(aid)
        assert retrieved is not None
        assert retrieved.html == "<h1>Test</h1>"
        assert retrieved.title == "Test Artifact"
        assert retrieved.query == "test query"

    def test_get_missing_returns_none(self):
        assert self.store.get("nonexistent-id") is None

    def test_save_returns_unique_ids(self):
        a1 = self.store.save(Artifact(html="<p>1</p>"))
        a2 = self.store.save(Artifact(html="<p>2</p>"))
        assert a1 != a2

    def test_max_artifacts_evicts_oldest(self):
        store = ArtifactStore(max_artifacts=3, ttl_seconds=60)
        ids = []
        for i in range(5):
            ids.append(store.save(Artifact(html=f"<p>{i}</p>")))

        # First two should be evicted
        assert store.get(ids[0]) is None
        assert store.get(ids[1]) is None
        # Last three should still exist
        assert store.get(ids[2]) is not None
        assert store.get(ids[3]) is not None
        assert store.get(ids[4]) is not None

    def test_ttl_expires_artifacts(self):
        store = ArtifactStore(max_artifacts=10, ttl_seconds=0.1)
        aid = store.save(Artifact(html="<p>expire me</p>"))
        assert store.get(aid) is not None
        time.sleep(0.15)
        assert store.get(aid) is None

    def test_list_returns_metadata(self):
        self.store.save(Artifact(html="<p>A</p>", title="Alpha", query="q1"))
        self.store.save(Artifact(html="<p>B</p>", title="Beta", query="q2"))
        items = self.store.list()
        assert len(items) == 2
        assert items[0]["title"] == "Alpha"
        assert items[1]["title"] == "Beta"
        assert "id" in items[0]
        assert "created_at" in items[0]
        # list should NOT include full html
        assert "html" not in items[0]

    def test_artifact_created_at_is_set(self):
        art = Artifact(html="<p>time</p>")
        aid = self.store.save(art)
        retrieved = self.store.get(aid)
        assert retrieved.created_at > 0


class TestArtifactModel:
    def test_defaults(self):
        art = Artifact(html="<div/>")
        assert art.title == ""
        assert art.query == ""
        assert art.created_at == 0.0

    def test_full_construction(self):
        art = Artifact(
            html="<p>hi</p>",
            title="My Artifact",
            query="what ships",
            artifact_type="dashboard",
        )
        assert art.artifact_type == "dashboard"
