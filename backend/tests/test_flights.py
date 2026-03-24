"""Tests for flight fetcher — viewport-aware region logic."""
import math
from unittest.mock import patch, MagicMock
from services.fetchers.flights import _point_in_any_region, _fetch_adsb_lol_regions


STATIC_REGIONS = [
    {"lat": 39.8, "lon": -98.5, "dist": 2000},
    {"lat": 50.0, "lon": 15.0, "dist": 2000},
    {"lat": 25.0, "lon": 65.0, "dist": 2000},
    {"lat": 35.0, "lon": 105.0, "dist": 2000},
    {"lat": -25.0, "lon": 133.0, "dist": 2000},
    {"lat": 0.0, "lon": 20.0, "dist": 2500},
    {"lat": -15.0, "lon": -60.0, "dist": 2000},
]


class TestPointInAnyRegion:
    def test_inside_usa_region(self):
        assert _point_in_any_region(40.0, -90.0, STATIC_REGIONS)

    def test_inside_europe_region(self):
        assert _point_in_any_region(48.0, 2.0, STATIC_REGIONS)

    def test_inside_south_asia_region(self):
        assert _point_in_any_region(30.0, 70.0, STATIC_REGIONS)

    def test_outside_all_regions_pacific(self):
        """Central Pacific — no static region covers this."""
        assert not _point_in_any_region(10.0, -170.0, STATIC_REGIONS)

    def test_outside_all_regions_mid_pacific(self):
        """Mid-Pacific near Hawaii — outside all static circles."""
        assert not _point_in_any_region(20.0, -155.0, STATIC_REGIONS)


class TestViewportBonusRegion:
    @patch("services.fetchers.flights.fetch_with_curl")
    def test_bonus_added_for_dead_zone(self, mock_curl):
        """When viewport is in a dead zone, an extra region should be fetched."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ac": []}
        mock_curl.return_value = mock_resp

        # Pacific viewport — outside all static regions
        viewport = {"s": 5.0, "w": -175.0, "n": 15.0, "e": -165.0}
        with patch("services.fetchers._store._current_viewport", viewport):
            _fetch_adsb_lol_regions()

        # 7 static + 1 bonus = 8 calls
        assert mock_curl.call_count == 8

    @patch("services.fetchers.flights.fetch_with_curl")
    def test_no_bonus_for_covered_area(self, mock_curl):
        """When viewport is inside a static region, no bonus region added."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ac": []}
        mock_curl.return_value = mock_resp

        # New York viewport — inside USA region
        viewport = {"s": 40.0, "w": -74.5, "n": 41.0, "e": -73.5}
        with patch("services.fetchers._store._current_viewport", viewport):
            _fetch_adsb_lol_regions()

        # Only 7 static, no bonus
        assert mock_curl.call_count == 7

    @patch("services.fetchers.flights.fetch_with_curl")
    def test_no_bonus_when_no_viewport(self, mock_curl):
        """When no viewport has been set, no bonus region added."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ac": []}
        mock_curl.return_value = mock_resp

        with patch("services.fetchers._store._current_viewport", None):
            _fetch_adsb_lol_regions()

        assert mock_curl.call_count == 7

    @patch("services.fetchers.flights.fetch_with_curl")
    def test_antimeridian_viewport_centers_correctly(self, mock_curl):
        """Viewport crossing 180° should center in the Pacific, not Atlantic."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ac": []}
        mock_curl.return_value = mock_resp

        # Viewport straddling antimeridian: 170E to 170W
        viewport = {"s": -5.0, "w": 170.0, "n": 5.0, "e": -170.0}
        with patch("services.fetchers._store._current_viewport", viewport):
            _fetch_adsb_lol_regions()

        # Should get a bonus region (Pacific is a dead zone)
        assert mock_curl.call_count == 8
        # Verify the bonus region's longitude is near 180, not near 0
        last_call_url = mock_curl.call_args_list[-1][0][0]
        # URL format: .../lon/{lon}/...
        lon_str = last_call_url.split("/lon/")[1].split("/")[0]
        bonus_lon = float(lon_str)
        assert abs(bonus_lon) > 150, f"Bonus lon {bonus_lon} should be near ±180, not 0"
