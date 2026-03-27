/**
 * Dummy data fixture for ChokePoint Risk Monitor.
 * Realistic OSINT-style data across 6 chokepoints.
 * ONLY use when explicitly requested — never in production.
 */

export interface ChokeData {
  ships?: Array<{ name?: string; callsign?: string; type?: string; ship_type?: string; flag?: string; lat?: number; lng?: number; yacht_alert?: boolean; plan_name?: string }>;
  tracked_ships?: Array<{ name?: string; callsign?: string; type?: string; flag?: string; lat?: number; lng?: number; yacht_alert?: boolean; plan_name?: string }>;
  military_flights?: Array<{ callsign?: string; registration?: string; type?: string; aircraft_type?: string; lat?: number; lng?: number }>;
  gdelt_events?: Array<{ event_type?: string; EventCode?: string; goldstein_scale?: number; GoldsteinScale?: number; lat?: number; lng?: number }>;
  gps_jamming?: Array<{ lat?: number; lng?: number; radius?: number }>;
  fires?: Array<{ lat?: number; lng?: number; brightness?: number; bright_ti4?: number }>;
  oil_prices?: { wti?: { price?: number; change_pct?: number }; brent?: { price?: number; change_pct?: number } };
}

export const DUMMY_CHOKEPOINT_DATA: ChokeData = {
  ships: [
    // Strait of Hormuz cluster
    { name: "PACIFIC VOYAGER", callsign: "V7GX3", type: "tanker", flag: "MH", lat: 26.56, lng: 56.25 },
    { name: "STENA IMPERO", callsign: "MHCS2", type: "tanker", flag: "GB", lat: 26.58, lng: 56.30 },
    { name: "FRONT ALTAIR", callsign: "VRBY7", type: "tanker", flag: "MH", lat: 26.52, lng: 56.22 },
    { name: "NAVE ANDROMEDA", callsign: "IBNH", type: "tanker", flag: "IT", lat: 26.60, lng: 56.35 },
    { name: "AL MARIYAH", callsign: "A6E2345", type: "cargo", flag: "AE", lat: 26.50, lng: 56.18 },
    // Strait of Malacca
    { name: "EVERGREEN HARMONY", callsign: "BPJN", type: "container", flag: "PA", lat: 1.45, lng: 103.80 },
    { name: "COSCO SHIPPING ARIES", callsign: "VRQD3", type: "container", flag: "HK", lat: 1.40, lng: 103.75 },
    { name: "MARAN GAS CORONIS", callsign: "SVQR", type: "lng_tanker", flag: "GR", lat: 1.52, lng: 103.90 },
    // Suez Canal
    { name: "MSC ANNA", callsign: "3FZB9", type: "container", flag: "PA", lat: 30.45, lng: 32.35 },
    { name: "NISSOS RHENIA", callsign: "SVAB7", type: "tanker", flag: "GR", lat: 30.40, lng: 32.33 },
    // Bab el-Mandeb
    { name: "GALAXY LEADER", callsign: "C4QA2", type: "car_carrier", flag: "BS", lat: 12.60, lng: 43.30 },
    { name: "MARLIN LUANDA", callsign: "VRBO9", type: "tanker", flag: "MH", lat: 12.55, lng: 43.25 },
    // Panama Canal
    { name: "NEOPANAMAX PIONEER", callsign: "HP1234", type: "container", flag: "PA", lat: 9.08, lng: -79.68 },
    // GIUK Gap
    { name: "NORTHERN SPIRIT", callsign: "LATO7", type: "cargo", flag: "NO", lat: 63.50, lng: -12.00 },
    // Military vessels
    { name: "USS EISENHOWER", type: "carrier", flag: "US", lat: 26.65, lng: 56.40 },
    { name: "USS GRAVELY", type: "military_vessel", flag: "US", lat: 12.58, lng: 43.28 },
    { name: "LIAONING", type: "carrier", flag: "CN", lat: 1.60, lng: 104.00 },
  ],

  tracked_ships: [
    { name: "USS EISENHOWER", type: "carrier", flag: "US", lat: 26.65, lng: 56.40, plan_name: "CVN-69" },
    { name: "USS GRAVELY", type: "military_vessel", flag: "US", lat: 12.58, lng: 43.28, plan_name: "DDG-107" },
    { name: "LIAONING", type: "carrier", flag: "CN", lat: 1.60, lng: 104.00, plan_name: "CV-16" },
    { name: "GALAXY LEADER", type: "car_carrier", flag: "BS", lat: 12.60, lng: 43.30, yacht_alert: true },
  ],

  military_flights: [
    // Hormuz patrol
    { callsign: "RCH451", type: "C-17A", aircraft_type: "transport", lat: 26.70, lng: 56.50 },
    { callsign: "EVAC11", type: "P-8A", aircraft_type: "maritime_patrol", lat: 26.40, lng: 55.80 },
    { callsign: "JAKE21", type: "MQ-9", aircraft_type: "uav", lat: 26.55, lng: 56.10 },
    // Bab el-Mandeb
    { callsign: "TOPCAT7", type: "F/A-18E", aircraft_type: "fighter", lat: 12.70, lng: 43.40 },
    { callsign: "NAVY5E", type: "E-2D", aircraft_type: "awacs", lat: 12.80, lng: 43.50 },
    // Malacca
    { callsign: "RSAF42", type: "F-16D", aircraft_type: "fighter", lat: 1.50, lng: 103.85 },
    // GIUK
    { callsign: "NATO01", type: "P-8A", aircraft_type: "maritime_patrol", lat: 63.80, lng: -11.50 },
  ],

  gdelt_events: [
    // Hormuz tensions
    { event_type: "PROTEST", goldstein_scale: -5.0, lat: 27.19, lng: 56.27 },
    { event_type: "MILITARY_EXERCISE", goldstein_scale: -3.0, lat: 26.30, lng: 56.00 },
    { event_type: "THREATEN", goldstein_scale: -7.0, lat: 26.80, lng: 56.60 },
    // Bab el-Mandeb / Red Sea
    { event_type: "USE_FORCE", goldstein_scale: -10.0, lat: 12.65, lng: 43.35 },
    { event_type: "ATTACK", goldstein_scale: -9.4, lat: 13.00, lng: 42.80 },
    { event_type: "THREATEN", goldstein_scale: -7.0, lat: 12.40, lng: 43.50 },
    // Suez area
    { event_type: "DIPLOMATIC_MEETING", goldstein_scale: 3.0, lat: 30.60, lng: 32.30 },
    // South China Sea
    { event_type: "MILITARY_EXERCISE", goldstein_scale: -4.0, lat: 1.80, lng: 104.20 },
    { event_type: "NAVAL_BLOCKADE", goldstein_scale: -8.0, lat: 1.20, lng: 103.50 },
  ],

  gps_jamming: [
    { lat: 26.55, lng: 56.20, radius: 80 },   // Hormuz
    { lat: 12.58, lng: 43.32, radius: 60 },   // Bab el-Mandeb
    { lat: 30.50, lng: 32.35, radius: 40 },   // Suez approach
  ],

  fires: [
    { lat: 26.48, lng: 56.15, brightness: 340 },  // Near Hormuz — possible flaring
    { lat: 12.50, lng: 43.20, brightness: 310 },  // Djibouti area
    { lat: 9.10, lng: -79.70, brightness: 290 },  // Near Panama — deforestation
    { lat: 30.55, lng: 32.40, brightness: 305 },  // Near Suez
  ],

  oil_prices: {
    wti: { price: 78.42, change_pct: -1.23 },
    brent: { price: 82.67, change_pct: -0.87 },
  },
};

/** Standardized dataset catalog for the artifacts showcase. */
export const DATASETS = [
  { key: "default", label: "6 GLOBAL CHOKEPOINTS", data: DUMMY_CHOKEPOINT_DATA },
] as const;
