"""Tests for the cross-domain post-processing pipeline."""
import pytest

from services.post_processing import (
    compute_coverage_gaps,
    compute_cross_domain_correlations,
    populate_machine_assessments,
    post_process_slow_data,
)


# --- Coverage Gaps ---

def test_coverage_gaps_basic():
    """GDELT events in a cell with no news → gap detected."""
    gdelt = [{"lat": 10.0, "lon": 20.0, "event_root_code": "18"} for _ in range(5)]
    news = []
    gaps = compute_coverage_gaps(gdelt, news)
    assert len(gaps) == 1
    assert gaps[0]["gdelt_count"] == 5
    assert gaps[0]["news_count"] == 0


def test_coverage_gaps_below_threshold():
    """Fewer than COVERAGE_GAP_MIN_GDELT events → no gap reported."""
    gdelt = [{"lat": 10.0, "lon": 20.0, "event_root_code": "14"} for _ in range(2)]
    news = []
    gaps = compute_coverage_gaps(gdelt, news)
    assert gaps == []


def test_coverage_gaps_with_news_coverage():
    """GDELT + news in the same cell → no gap."""
    gdelt = [{"lat": 10.0, "lon": 20.0, "event_root_code": "19"} for _ in range(5)]
    news = [{"lat": 9.0, "lon": 19.0}]  # Same grid cell at 4-degree resolution (both round to 8,20)
    gaps = compute_coverage_gaps(gdelt, news)
    assert gaps == []


def test_coverage_gaps_empty_gdelt():
    """Empty GDELT → no gaps, no crash."""
    assert compute_coverage_gaps([], [{"lat": 1, "lon": 2}]) == []


# --- Cross-Domain Correlations ---

def test_cross_domain_military_near_conflict():
    """Military flight within 500km of GDELT hotspot → correlation."""
    gdelt = [{"lat": 35.0, "lon": 45.0, "action_geo": "Iraq"} for _ in range(5)]
    military = [{"lat": 35.5, "lng": 45.5, "callsign": "RCH123", "type": "C-17", "country": "US"}]
    fires = []
    outages = []
    correlations = compute_cross_domain_correlations(gdelt, military, fires, outages)
    mil_corrs = [c for c in correlations if c["type"] == "military_near_conflict"]
    assert len(mil_corrs) >= 1
    assert mil_corrs[0]["entity"]["flight"] == "RCH123"


def test_cross_domain_fires_near_conflict():
    """Fire clusters within 300km of conflict zone → correlation."""
    gdelt = [{"lat": 35.0, "lon": 45.0, "action_geo": "Iraq"} for _ in range(5)]
    military = []
    fires = [{"lat": 35.1, "lng": 45.1} for _ in range(3)]
    outages = []
    correlations = compute_cross_domain_correlations(gdelt, military, fires, outages)
    fire_corrs = [c for c in correlations if c["type"] == "fires_near_conflict"]
    assert len(fire_corrs) >= 1
    assert fire_corrs[0]["fire_count"] == 3


def test_cross_domain_empty_gdelt():
    """No GDELT events → no correlations, no crash."""
    assert compute_cross_domain_correlations([], [{"lat": 1, "lon": 2}], [], []) == []


# --- Machine Assessments ---

def test_machine_assessments_enrichment():
    """News item near GDELT events gets machine_assessment field."""
    news = [{"coords": [35.0, 45.0], "title": "Test article"}]
    gdelt = [{"lat": 35.1, "lon": 45.1} for _ in range(3)]
    fires = []
    outages = []
    populate_machine_assessments(news, gdelt, fires, outages)
    assert "machine_assessment" in news[0]
    assert news[0]["machine_assessment"]["gdelt_nearby"] >= 3


def test_machine_assessments_no_coords():
    """News items without coordinates are skipped gracefully."""
    news = [{"title": "No coords"}, {"coords": None}]
    gdelt = [{"lat": 10.0, "lon": 20.0}]
    populate_machine_assessments(news, gdelt, [], [])
    assert "machine_assessment" not in news[0]
    assert "machine_assessment" not in news[1]


# --- Integration: post_process_slow_data ---

def test_post_process_slow_data_writes_to_store():
    """Entry point reads from store and writes coverage_gaps + correlations back."""
    store = {
        "gdelt": [{"lat": 10.0, "lon": 20.0, "event_root_code": "18"} for _ in range(5)],
        "news": [],
        "military_flights": [],
        "firms_fires": [],
        "internet_outages": [],
        "coverage_gaps": [],
        "correlations": [],
    }
    post_process_slow_data(store)
    assert isinstance(store["coverage_gaps"], list)
    assert isinstance(store["correlations"], list)
    assert len(store["coverage_gaps"]) >= 1


def test_geojson_gdelt_normalization():
    """GDELT stored as GeoJSON Features are normalized before processing."""
    geojson_gdelt = [
        {
            "type": "Feature",
            "properties": {"name": "Baghdad, Iraq", "count": 3},
            "geometry": {"type": "Point", "coordinates": [44.4, 33.3]},
        }
        for _ in range(5)
    ]
    store = {
        "gdelt": geojson_gdelt,
        "news": [],
        "military_flights": [],
        "firms_fires": [],
        "internet_outages": [],
    }
    post_process_slow_data(store)
    # GeoJSON features should be normalized and produce coverage gaps
    assert len(store["coverage_gaps"]) >= 1
    gap = store["coverage_gaps"][0]
    assert gap["gdelt_count"] == 5


def test_empty_data_no_crash():
    """Completely empty store → empty results, no exceptions."""
    store = {
        "gdelt": [],
        "news": [],
        "military_flights": [],
        "firms_fires": [],
        "internet_outages": [],
    }
    post_process_slow_data(store)
    assert store.get("coverage_gaps") == []
    assert store.get("correlations") == []
