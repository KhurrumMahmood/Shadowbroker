"""WHO Disease Outbreak News (DON) fetcher."""
import logging
from services.fetchers.retry import with_retry
from services.fetchers._store import latest_data, _mark_fresh, _data_lock
from services.network_utils import fetch_with_curl

logger = logging.getLogger(__name__)

_WHO_DON_URL = "https://www.who.int/api/news/diseaseoutbreaknews"

_SEVERITY = {
    "ebola": 9, "marburg": 9,
    "mers": 7, "avian influenza": 7, "h5n1": 7, "nipah": 7,
    "cholera": 6, "plague": 6, "yellow fever": 6,
    "dengue": 5, "mpox": 5, "lassa fever": 5,
}


def _parse_title(title: str) -> tuple[str, str]:
    """Extract (disease_name, country) from DON title like 'Ebola virus disease \u2013 Uganda'."""
    for sep in (" \u2013 ", " - "):
        if sep in title:
            disease, country = title.split(sep, 1)
            return disease.strip(), country.strip()
    return title, ""


def _severity_score(disease: str) -> int:
    """Assign risk score based on disease severity."""
    lower = disease.lower()
    for keyword, score in _SEVERITY.items():
        if keyword in lower:
            return score
    return 3


@with_retry(max_retries=1, base_delay=5)
def fetch_disease_outbreaks():
    """Fetch recent WHO Disease Outbreak News."""
    from services.fetchers.news import _resolve_coords

    resp = fetch_with_curl(_WHO_DON_URL, timeout=15)
    raw = resp.json()

    # API returns {"value": [...]} or a direct list
    items = raw.get("value", raw) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        logger.warning("WHO DON: unexpected response format")
        return

    def _field(item: dict, pascal: str, camel: str, default=""):
        return item.get(pascal) or item.get(camel, default)

    outbreaks = []
    for item in items[:30]:
        title = _field(item, "Title", "title")
        disease_name, country = _parse_title(title)
        coords = _resolve_coords(f"{country} {disease_name}")

        outbreaks.append({
            "id": _field(item, "Id", "id"),
            "title": title,
            "disease_name": disease_name,
            "country": country,
            "summary": _field(item, "Summary", "summary")[:300],
            "pub_date": _field(item, "DatePublished", "datePublished"),
            "risk_score": _severity_score(disease_name),
            "lat": coords[0] if coords else None,
            "lng": coords[1] if coords else None,
            "link": _field(item, "Url", "url"),
            "source": "WHO DON",
        })

    with _data_lock:
        latest_data["disease_outbreaks"] = outbreaks
    if outbreaks:
        _mark_fresh("disease_outbreaks")
    logger.info(f"WHO DON: {len(outbreaks)} outbreaks fetched")
