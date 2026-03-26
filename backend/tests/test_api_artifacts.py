"""Tests for artifact search and version listing API endpoints."""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Route ordering — regression test for the route collision bug
# ---------------------------------------------------------------------------

class TestRouteOrdering:
    """Verify /api/artifacts/registry is NOT caught by /api/artifacts/{artifact_id}."""

    @pytest.fixture
    def mock_registry(self):
        registry = MagicMock()
        registry.list_all.return_value = []
        with patch(
            "services.agent.artifact_registry.get_artifact_registry",
            return_value=registry,
        ):
            yield registry

    def test_registry_not_caught_by_artifact_id(self, client, mock_registry):
        """GET /api/artifacts/registry should return a list, not a 404 from artifact store."""
        resp = client.get("/api/artifacts/registry")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_registry_search_not_caught_by_artifact_id(self, client, mock_registry):
        """GET /api/artifacts/registry/search should return 200, not match {artifact_id}."""
        resp = client.get("/api/artifacts/registry/search?tags=test")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Registry entry and version endpoints
# ---------------------------------------------------------------------------

class TestRegistryEntryEndpoint:
    """GET /api/artifacts/registry/{name} and /api/artifacts/registry/{name}/v/{version}"""

    @pytest.fixture
    def mock_registry(self):
        registry = MagicMock()
        with patch(
            "services.agent.artifact_registry.get_artifact_registry",
            return_value=registry,
        ):
            yield registry

    def test_returns_meta_for_existing_artifact(self, client, mock_registry):
        mock_registry.get_latest_version.return_value = (
            "<html>...</html>",
            {"name": "ship-map", "title": "Ship Map", "current_version": 2, "versions": []},
        )
        resp = client.get("/api/artifacts/registry/ship-map")
        assert resp.status_code == 200
        assert resp.json()["name"] == "ship-map"

    def test_404_for_missing_entry(self, client, mock_registry):
        mock_registry.get_latest_version.return_value = None
        resp = client.get("/api/artifacts/registry/nonexistent")
        assert resp.status_code == 404

    def test_get_specific_version(self, client, mock_registry):
        mock_registry.get_version.return_value = "<html>v1</html>"
        resp = client.get("/api/artifacts/registry/ship-map/v/1")
        assert resp.status_code == 200
        assert "v1" in resp.text

    def test_version_404(self, client, mock_registry):
        mock_registry.get_version.return_value = None
        resp = client.get("/api/artifacts/registry/ship-map/v/99")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------

class TestSearchEndpoint:
    """GET /api/artifacts/registry/search?tags=..."""

    @pytest.fixture
    def mock_registry(self):
        registry = MagicMock()
        with patch(
            "services.agent.artifact_registry.get_artifact_registry",
            return_value=registry,
        ):
            yield registry

    def test_returns_matches(self, client, mock_registry):
        mock_registry.search.return_value = [
            {"name": "ship-map", "tags": ["maritime", "map"], "current_version": 2},
        ]
        resp = client.get("/api/artifacts/registry/search?tags=maritime,map")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "ship-map"
        mock_registry.search.assert_called_once_with(["maritime", "map"])

    def test_returns_empty_for_no_match(self, client, mock_registry):
        mock_registry.search.return_value = []
        resp = client.get("/api/artifacts/registry/search?tags=nonexistent")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_empty_for_blank_tags(self, client, mock_registry):
        resp = client.get("/api/artifacts/registry/search?tags=")
        assert resp.status_code == 200
        assert resp.json() == []
        mock_registry.search.assert_not_called()

    def test_returns_empty_for_missing_tags_param(self, client, mock_registry):
        resp = client.get("/api/artifacts/registry/search")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_ranked_by_score(self, client, mock_registry):
        mock_registry.search.return_value = [
            {"name": "best", "tags": ["a", "b", "c"]},
            {"name": "good", "tags": ["a", "b"]},
        ]
        resp = client.get("/api/artifacts/registry/search?tags=a,b,c")
        data = resp.json()
        assert data[0]["name"] == "best"
        assert data[1]["name"] == "good"


# ---------------------------------------------------------------------------
# Versions endpoint
# ---------------------------------------------------------------------------

class TestVersionsEndpoint:
    """GET /api/artifacts/registry/{name}/versions"""

    @pytest.fixture
    def mock_registry(self):
        registry = MagicMock()
        with patch(
            "services.agent.artifact_registry.get_artifact_registry",
            return_value=registry,
        ):
            yield registry

    def test_returns_version_list(self, client, mock_registry):
        mock_registry.get_latest_version.return_value = (
            "<html>...</html>",
            {
                "name": "ship-map",
                "current_version": 2,
                "versions": [
                    {"version": 1, "note": "initial", "created_at": "2026-03-20"},
                    {"version": 2, "note": "filters added", "created_at": "2026-03-21"},
                ],
            },
        )
        resp = client.get("/api/artifacts/registry/ship-map/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["version"] == 1
        assert data[1]["version"] == 2

    def test_404_for_missing_artifact(self, client, mock_registry):
        mock_registry.get_latest_version.return_value = None
        resp = client.get("/api/artifacts/registry/nonexistent/versions")
        assert resp.status_code == 404
        assert "error" in resp.json()
