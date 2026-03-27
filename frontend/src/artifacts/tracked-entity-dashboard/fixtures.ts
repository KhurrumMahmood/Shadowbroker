/**
 * Dummy data fixture for Tracked Entity Dashboard.
 * Notable vessels, military flights, and carrier groups.
 * ONLY use when explicitly requested — never in production.
 */

export interface TrackedData {
  tracked_ships?: Array<{ name: string; type?: string; lat?: number; lng?: number; flag?: string; owner?: string; mmsi?: string }>;
  military_flights?: Array<{ callsign?: string; type?: string; lat?: number; lng?: number; altitude?: number; squawk?: string; hex?: string }>;
  carriers?: Array<{ name: string; location?: string; status?: string; lat?: number; lng?: number }>;
}

export const DUMMY_TRACKED_DATA: TrackedData = {
  tracked_ships: [
    { name: "FLYING FOX", type: "yacht", flag: "KY", lat: 25.28, lng: 55.30, owner: "Dieter Schwarz", mmsi: "319123400" },
    { name: "DILBAR", type: "yacht", flag: "MT", lat: 43.70, lng: 7.27, owner: "Alisher Usmanov (sanctioned)", mmsi: "248012345" },
    { name: "AMADEA", type: "yacht", flag: "KY", lat: 18.45, lng: -66.10, owner: "DOJ-seized (Kerimov)", mmsi: "319098765" },
    { name: "RONGCHENG", type: "military_vessel", flag: "CN", lat: 10.30, lng: 114.50, mmsi: "413000789" },
    { name: "IRGCN PATROL 7", type: "military_vessel", flag: "IR", lat: 26.50, lng: 56.05, mmsi: "422012345" },
    { name: "CCG 5901", type: "military_vessel", flag: "CN", lat: 14.80, lng: 116.20, owner: "China Coast Guard", mmsi: "413999888" },
    { name: "AKADEMIK CHERSKIY", type: "research", flag: "RU", lat: 55.30, lng: 14.50, owner: "Gazprom Fleet", mmsi: "273456789" },
    { name: "STENA IMPERO", type: "tanker", flag: "GB", lat: 26.58, lng: 56.30, mmsi: "235098123" },
  ],

  military_flights: [
    { callsign: "SAM387", type: "VC-25A (Air Force One)", lat: 38.85, lng: -77.04, altitude: 35000, squawk: "0001", hex: "AE0001" },
    { callsign: "FORTE12", type: "RQ-4B Global Hawk", lat: 44.50, lng: 34.00, altitude: 55000, squawk: "7700", hex: "AE1234" },
    { callsign: "JAKE21", type: "MQ-9 Reaper", lat: 26.55, lng: 56.10, altitude: 25000, hex: "AE5678" },
    { callsign: "EVAC11", type: "P-8A Poseidon", lat: 26.40, lng: 55.80, altitude: 28000, hex: "AE9012" },
    { callsign: "RCH451", type: "C-17A Globemaster III", lat: 26.70, lng: 56.50, altitude: 32000, hex: "AE3456" },
    { callsign: "DUKE01", type: "RC-135W Rivet Joint", lat: 44.80, lng: 33.50, altitude: 34000, hex: "AE7890" },
    { callsign: "NCHO44", type: "E-3G Sentry (AWACS)", lat: 25.80, lng: 55.20, altitude: 29000, hex: "AE2345" },
    { callsign: "NATO01", type: "P-8A Poseidon", lat: 63.80, lng: -11.50, altitude: 27000, hex: "43C001" },
    { callsign: "TOPCAT7", type: "F/A-18E Super Hornet", lat: 12.70, lng: 43.40, altitude: 18000, hex: "AE6789" },
  ],

  carriers: [
    { name: "USS Dwight D. Eisenhower (CVN-69)", lat: 26.65, lng: 56.40, location: "Gulf of Oman", status: "Deployed — CSG-2" },
    { name: "USS Theodore Roosevelt (CVN-71)", lat: 7.50, lng: 72.00, location: "Indian Ocean", status: "Transit to CENTCOM AOR" },
    { name: "Liaoning (CV-16)", lat: 10.30, lng: 114.20, location: "South China Sea", status: "Exercises — Carrier Group" },
    { name: "Shandong (CV-17)", lat: 18.20, lng: 110.50, location: "South China Sea", status: "Port call — Hainan" },
    { name: "Charles de Gaulle (R91)", lat: 35.40, lng: 16.50, location: "Central Mediterranean", status: "NATO Patrol — CTF-473" },
    { name: "INS Vikrant (R11)", lat: 15.40, lng: 73.80, location: "Arabian Sea", status: "Sea Trials" },
  ],
};

/** Standardized dataset catalog for the artifacts showcase. */
export const DATASETS = [
  { key: "default", label: "YACHTS / MILITARY / CARRIERS", data: DUMMY_TRACKED_DATA },
] as const;
