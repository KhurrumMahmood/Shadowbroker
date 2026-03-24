"""Tests for GDELT quality filters in geopolitics._parse_gdelt_export_zip."""
import csv
import io
import zipfile

import pytest

from services.geopolitics import _parse_gdelt_export_zip


def _make_gdelt_zip(rows: list[list[str]]) -> bytes:
    """Build a minimal GDELT export ZIP from a list of 61-column TSV rows."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        tsv = io.StringIO()
        writer = csv.writer(tsv, delimiter="\t")
        for row in rows:
            # Pad to 61 columns if short
            padded = row + [""] * (61 - len(row))
            writer.writerow(padded)
        zf.writestr("test.export.CSV", tsv.getvalue())
    return buf.getvalue()


def _base_row(
    event_code="18",
    goldstein="-7.0",
    num_mentions="5",
    lat="48.8566",
    lng="2.3522",
    actor1_cc="FRA",
    actor2_cc="",
    action_geo_cc="FR",
) -> list[str]:
    """Return a 61-column GDELT row with sane defaults (ASSAULT, hostile, 5 mentions, Paris)."""
    row = [""] * 61
    row[6] = "France"          # Actor1Name
    row[7] = actor1_cc         # Actor1CountryCode
    row[16] = "Germany"        # Actor2Name
    row[17] = actor2_cc        # Actor2CountryCode
    row[26] = event_code       # EventCode
    row[30] = goldstein        # GoldsteinScale
    row[31] = num_mentions     # NumMentions
    row[52] = "Paris, France"  # ActionGeo_FullName
    row[53] = action_geo_cc    # ActionGeo_CountryCode
    row[56] = lat              # ActionGeo_Lat
    row[57] = lng              # ActionGeo_Long
    row[60] = "https://example.com/article"  # SOURCEURL
    return row


CONFLICT_CODES = {"17", "18", "19", "20"}


class TestCameoCodeFilter:
    def test_cameo_14_protest_rejected(self):
        """CAMEO 14 (PROTEST) should be filtered out."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(event_code="140")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 0

    def test_cameo_18_assault_accepted(self):
        """CAMEO 18 (ASSAULT) should pass through."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(event_code="182")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1

    def test_cameo_20_mass_violence_accepted(self):
        """CAMEO 20 (MASS VIOLENCE) should pass through."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(event_code="200")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1


class TestGoldsteinFilter:
    def test_hostile_passes(self):
        """Goldstein -7.0 (hostile) should pass."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(goldstein="-7.0")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1

    def test_threshold_passes(self):
        """Goldstein -3.0 (exactly at threshold) should pass."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(goldstein="-3.0")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1

    def test_not_hostile_rejected(self):
        """Goldstein -1.0 (not hostile enough) should be rejected."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(goldstein="-1.0")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 0

    def test_positive_rejected(self):
        """Goldstein +3.4 (cooperative) should be rejected."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(goldstein="3.4")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 0

    def test_missing_goldstein_passes(self):
        """Empty Goldstein field should pass (don't reject on missing data)."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(goldstein="")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1


class TestNumMentionsFilter:
    def test_high_mentions_passes(self):
        """10 mentions should pass."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(num_mentions="10")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1

    def test_threshold_passes(self):
        """3 mentions (exactly at threshold) should pass."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(num_mentions="3")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1

    def test_low_mentions_rejected(self):
        """1 mention should be rejected."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(num_mentions="1")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 0

    def test_missing_mentions_passes(self):
        """Empty NumMentions should pass."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(num_mentions="")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1


class TestGeoRelevanceFilter:
    """Tests for the existing geographic relevance filter (actor country vs geo country)."""

    def test_matching_actor_passes(self):
        """Event where actor1 matches geo country should pass."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(actor1_cc="FR", actor2_cc="DEU", action_geo_cc="FR")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1

    def test_neither_actor_matches_rejected(self):
        """Event where neither actor matches geo country should be rejected."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(actor1_cc="USA", actor2_cc="IRN", action_geo_cc="TZ")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 0

    def test_missing_actor_passes(self):
        """Event where actor country is empty should pass (conservative)."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row(actor1_cc="", actor2_cc="IRN", action_geo_cc="TZ")])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1


class TestCombinedFilters:
    def test_good_event_passes_all(self):
        """An event that meets all criteria should pass."""
        features, seen = [], set()
        zip_bytes = _make_gdelt_zip([_base_row()])
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 1

    def test_multiple_events_mixed(self):
        """Mix of good and bad events — only good ones survive."""
        rows = [
            _base_row(),                                    # good
            _base_row(event_code="140"),                    # bad: PROTEST
            _base_row(goldstein="-1.0"),                    # bad: not hostile
            _base_row(num_mentions="1"),                    # bad: low mentions
            _base_row(goldstein="-5.0", num_mentions="10"), # good
        ]
        # Second good row needs different location to avoid dedup
        rows[4][56] = "51.5074"
        rows[4][57] = "-0.1278"
        rows[4][52] = "London, UK"

        features, seen = [], set()
        zip_bytes = _make_gdelt_zip(rows)
        _parse_gdelt_export_zip(zip_bytes, CONFLICT_CODES, seen, features, {})
        assert len(features) == 2
