"""Tests for artifact search and version listing API endpoints."""
import pytest
from unittest.mock import patch, MagicMock


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
