"""CO2 emissions estimator for tracked aircraft.

Pure calculation — no API calls. Uses ICAO type codes to look up
approximate fuel burn rates, then converts to CO2 kg/hr.

Enriches tracked_flights entries in latest_data with a co2_kg_hr field.
Ported from upstream BigBodyCobain/Shadowbroker v0.9.6.
"""

import logging

from services.fetchers._store import latest_data, _data_lock

logger = logging.getLogger(__name__)

# Fuel burn rates (kg/hr) by ICAO type designator.
# Source: ICAO Aircraft Engine Emissions Databank + public flight ops data.
# CO2 = fuel_burn_kg_hr * 3.16 (standard aviation fuel conversion factor)
_FUEL_BURN_KG_HR: dict[str, float] = {
    # Wide-body airliners
    "A388": 11700, "B744": 10800, "B748": 10200, "A346": 8500,
    "B77W": 7800, "B772": 7200, "B773": 7500, "A333": 5800,
    "A332": 5500, "A359": 5800, "A35K": 6200, "B789": 5400,
    "B78X": 5600, "B788": 5000,
    # Narrow-body airliners
    "A321": 2800, "A320": 2500, "A319": 2300, "B738": 2600,
    "B739": 2500, "B737": 2400, "B38M": 2400, "B39M": 2500,
    "A20N": 2300, "A21N": 2600, "E195": 2000, "E190": 1800,
    "B752": 3400, "B753": 3600,
    # Regional / turboprops
    "E170": 1600, "E175": 1700, "CRJ9": 1500, "CRJ7": 1300,
    "DH8D": 800, "AT76": 600, "AT72": 550,
    # Business jets
    "GL7T": 1600, "GLEX": 1500, "GLF6": 1400, "GLF5": 1200,
    "GL5T": 1200, "CL35": 900, "C700": 1100, "C750": 1000,
    "C680": 800, "C560": 600, "LJ60": 500, "LJ45": 450,
    "FA7X": 1100, "FA8X": 1200, "F2TH": 900, "F900": 1000,
    "GALX": 900, "E55P": 700, "C25B": 400, "C25A": 380,
    "PC12": 250, "PC24": 450, "H25B": 700,
    # Military (common types)
    "C17": 8000, "C5M": 12000, "C130": 3500, "C30J": 3200,
    "KC10": 9000, "KC46": 7500, "KC35": 7000, "E3CF": 5500,
    "E6B": 5000, "P8A": 3000, "B52H": 8000, "B1B": 10000,
    "B2": 8500, "F16": 3500, "F15": 4500, "F18": 3800,
    "F22": 4000, "F35": 3500, "A10": 2500, "V22": 1800,
    "RQ4": 600, "MQ9": 180,
    # Helicopters
    "S92": 500, "H60": 450, "H47": 700, "UH1": 250,
    "EC35": 200, "A139": 350, "EC45": 250,
}

# CO2 conversion factor: 1 kg jet fuel ≈ 3.16 kg CO2
_CO2_FACTOR = 3.16

# Default fuel burn for unknown types (average narrow-body)
_DEFAULT_FUEL_BURN = 2500


def estimate_co2(icao_type: str | None) -> float:
    """Estimate CO2 kg/hr for an aircraft by ICAO type code."""
    if not icao_type:
        return round(_DEFAULT_FUEL_BURN * _CO2_FACTOR, 1)

    fuel_burn = _FUEL_BURN_KG_HR.get(icao_type.upper(), _DEFAULT_FUEL_BURN)
    return round(fuel_burn * _CO2_FACTOR, 1)


def enrich_emissions():
    """Add co2_kg_hr to all tracked flights in latest_data.

    Called as post-processing after flight fetch. Modifies in-place.
    """
    with _data_lock:
        tracked = latest_data.get("tracked_flights", [])
        if not tracked:
            return

        enriched = 0
        for flight in tracked:
            icao_type = flight.get("t") or flight.get("type_code") or flight.get("model")
            co2 = estimate_co2(icao_type)
            flight["co2_kg_hr"] = co2
            enriched += 1

        logger.info(f"Emissions: enriched {enriched} tracked flights with CO2 estimates")
