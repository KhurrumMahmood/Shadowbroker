/**
 * Dummy data fixture for SITREP Region Brief.
 * Simulates a Persian Gulf / Strait of Hormuz region brief.
 * ONLY use when explicitly requested — never in production.
 */

export interface SitrepData {
  region?: string;
  bbox?: { south: number; west: number; north: number; east: number };
  timeframe?: number;
  ships?: Array<{ name?: string; mmsi?: string; type?: string; flag?: string; lat?: number; lng?: number; tracked?: boolean; [k: string]: unknown }>;
  military_flights?: Array<{ callsign?: string; type?: string; aircraft_type?: string; lat?: number; lng?: number; [k: string]: unknown }>;
  gdelt_events?: Array<{ type?: string; event_type?: string; goldstein_scale?: number; lat?: number; lng?: number; [k: string]: unknown }>;
  fires?: Array<{ lat?: number; lng?: number; brightness?: number; [k: string]: unknown }>;
  gps_jamming?: Array<{ lat?: number; lng?: number; radius?: number; [k: string]: unknown }>;
  news?: Array<{ title?: string; source?: string; published?: string; [k: string]: unknown }>;
  assessment?: string;
}

export const DUMMY_SITREP_DATA: SitrepData = {
  region: "Strait of Hormuz / Persian Gulf",
  bbox: { south: 24.0, west: 54.0, north: 28.0, east: 58.0 },
  timeframe: 24,

  ships: [
    { name: "PACIFIC VOYAGER", mmsi: "538006789", type: "tanker", flag: "MH", lat: 26.56, lng: 56.25, tracked: false },
    { name: "STENA IMPERO", mmsi: "235098123", type: "tanker", flag: "GB", lat: 26.58, lng: 56.30, tracked: true },
    { name: "FRONT ALTAIR", mmsi: "538004567", type: "tanker", flag: "MH", lat: 26.52, lng: 56.22, tracked: true },
    { name: "NAVE ANDROMEDA", mmsi: "247012345", type: "tanker", flag: "IT", lat: 26.60, lng: 56.35, tracked: false },
    { name: "USS EISENHOWER", mmsi: "369970069", type: "carrier", flag: "US", lat: 26.65, lng: 56.40, tracked: true },
    { name: "ARTAVIUS", mmsi: "636019234", type: "tanker", flag: "LR", lat: 26.45, lng: 55.90, tracked: true },
    { name: "IRGCN PATROL 7", type: "military_vessel", flag: "IR", lat: 26.50, lng: 56.05, tracked: true },
    { name: "AL MARIYAH", mmsi: "470123456", type: "cargo", flag: "AE", lat: 26.50, lng: 56.18, tracked: false },
  ],

  military_flights: [
    { callsign: "RCH451", type: "C-17A", aircraft_type: "transport", lat: 26.70, lng: 56.50 },
    { callsign: "EVAC11", type: "P-8A", aircraft_type: "maritime_patrol", lat: 26.40, lng: 55.80 },
    { callsign: "JAKE21", type: "MQ-9", aircraft_type: "uav", lat: 26.55, lng: 56.10 },
    { callsign: "NCHO44", type: "E-3G", aircraft_type: "awacs", lat: 25.80, lng: 55.20 },
    { callsign: "IRGCAF3", type: "Su-24", aircraft_type: "strike", lat: 27.10, lng: 56.80 },
  ],

  gdelt_events: [
    { event_type: "THREATEN", goldstein_scale: -7.0, lat: 26.80, lng: 56.60 },
    { event_type: "MILITARY_EXERCISE", goldstein_scale: -3.0, lat: 26.30, lng: 56.00 },
    { event_type: "PROTEST", goldstein_scale: -5.0, lat: 27.19, lng: 56.27 },
    { event_type: "DIPLOMATIC_COOPERATION", goldstein_scale: 4.0, lat: 25.30, lng: 55.30 },
    { event_type: "SEIZE", goldstein_scale: -9.0, lat: 26.55, lng: 56.20 },
  ],

  fires: [
    { lat: 26.48, lng: 56.15, brightness: 340 },
    { lat: 27.00, lng: 56.70, brightness: 295 },
  ],

  gps_jamming: [
    { lat: 26.55, lng: 56.20, radius: 80 },
    { lat: 27.20, lng: 57.00, radius: 45 },
  ],

  news: [
    { title: "Iran seizes tanker in Strait of Hormuz amid rising tensions", source: "Reuters", published: "2026-03-26T06:30:00Z" },
    { title: "US carrier strike group enters Persian Gulf", source: "AP News", published: "2026-03-26T04:15:00Z" },
    { title: "GPS jamming incidents spike near Hormuz — maritime advisory issued", source: "Lloyd's List", published: "2026-03-25T22:00:00Z" },
    { title: "Oil prices dip on OPEC+ production signals", source: "Bloomberg", published: "2026-03-25T18:45:00Z" },
    { title: "UAE calls for de-escalation in Gulf shipping lanes", source: "Al Jazeera", published: "2026-03-25T14:20:00Z" },
  ],

  assessment: "ELEVATED RISK — Multiple indicators of rising tension in the Strait of Hormuz corridor. Iranian naval activity has increased with at least one tanker seizure reported in the last 24 hours. US CSG-2 (Eisenhower) is positioned in the Gulf of Oman providing overwatch. GPS jamming detected across two zones affecting commercial navigation. GDELT conflict scores averaging -5.8 across 5 events. Recommend heightened monitoring of IRGCN patrol patterns and tanker AIS gaps.",
};
