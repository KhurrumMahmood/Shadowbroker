"""Tests for the shared chokepoints module."""
import math
import pytest
from services.chokepoints import CHOKEPOINTS, chokepoint_bboxes


def test_chokepoints_exist():
    """At least 6 strategic chokepoints are defined."""
    assert len(CHOKEPOINTS) >= 6


def test_chokepoint_fields():
    """Each chokepoint has required fields."""
    for cp in CHOKEPOINTS:
        assert "name" in cp
        assert "lat" in cp
        assert "lng" in cp
        assert "radius_km" in cp
        assert -90 <= cp["lat"] <= 90
        assert -180 <= cp["lng"] <= 180
        assert cp["radius_km"] > 0


def test_bboxes_match_chokepoints():
    """chokepoint_bboxes returns one bbox per chokepoint."""
    bboxes = chokepoint_bboxes()
    assert len(bboxes) == len(CHOKEPOINTS)


def test_bbox_format():
    """Each bbox is [[south, west], [north, east]] with valid coords."""
    for bbox in chokepoint_bboxes():
        assert len(bbox) == 2
        south, west = bbox[0]
        north, east = bbox[1]
        assert south < north, f"south ({south}) must be < north ({north})"
        # West < east for most boxes (except if wrapping antimeridian)
        assert -90 <= south <= 90
        assert -90 <= north <= 90


def test_bbox_radius_correct():
    """Bbox dimensions roughly match the specified radius."""
    for cp, bbox in zip(CHOKEPOINTS, chokepoint_bboxes()):
        south, _ = bbox[0]
        north, _ = bbox[1]
        dlat = north - south
        actual_km = dlat * 111.0  # 1 deg ≈ 111 km
        expected_km = cp["radius_km"] * 2  # diameter
        # Allow 5% tolerance for rounding
        assert abs(actual_km - expected_km) < expected_km * 0.05, \
            f"{cp['name']}: expected ~{expected_km:.0f}km, got {actual_km:.0f}km"
