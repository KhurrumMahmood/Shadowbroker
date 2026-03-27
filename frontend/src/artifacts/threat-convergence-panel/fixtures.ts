/**
 * Dummy data fixture for Threat Convergence Panel.
 * Data is spatially clustered to trigger convergence zones (3+ domains in 2deg cells).
 * ONLY use when explicitly requested — never in production.
 */

export interface ConvergenceData {
  military_flights?: Array<{ callsign?: string; type?: string; aircraft_type?: string; lat?: number; lng?: number }>;
  gdelt_events?: Array<{ event_type?: string; goldstein_scale?: number; lat?: number; lng?: number }>;
  gps_jamming?: Array<{ lat?: number; lng?: number; radius?: number }>;
  fires?: Array<{ lat?: number; lng?: number; brightness?: number }>;
  ships?: Array<{ name?: string; type?: string; flag?: string; lat?: number; lng?: number }>;
}

export const DUMMY_CONVERGENCE_DATA: ConvergenceData = {
  // --- CLUSTER 1: Strait of Hormuz (~26-27N, 55-57E) ---
  // 5 domains present → strong convergence
  military_flights: [
    { callsign: "EVAC11", type: "P-8A", aircraft_type: "maritime_patrol", lat: 26.40, lng: 55.80 },
    { callsign: "JAKE21", type: "MQ-9", aircraft_type: "uav", lat: 26.55, lng: 56.10 },
    { callsign: "RCH451", type: "C-17A", aircraft_type: "transport", lat: 26.70, lng: 56.50 },
    // Cluster 2: Red Sea
    { callsign: "TOPCAT7", type: "F/A-18E", aircraft_type: "fighter", lat: 12.70, lng: 43.40 },
    { callsign: "NAVY5E", type: "E-2D", aircraft_type: "awacs", lat: 12.80, lng: 43.50 },
    // Cluster 3: Eastern Med
    { callsign: "IAF205", type: "F-35I", aircraft_type: "fighter", lat: 33.20, lng: 34.80 },
    { callsign: "FORTE12", type: "RQ-4B", aircraft_type: "uav", lat: 33.50, lng: 35.20 },
    // Cluster 4: South China Sea
    { callsign: "RSAF42", type: "F-16D", aircraft_type: "fighter", lat: 10.20, lng: 114.30 },
    // Cluster 5: Black Sea
    { callsign: "FORTE10", type: "RQ-4B", aircraft_type: "uav", lat: 44.50, lng: 34.00 },
    { callsign: "DUKE01", type: "RC-135W", aircraft_type: "sigint", lat: 44.80, lng: 33.50 },
  ],

  gdelt_events: [
    // Cluster 1: Hormuz
    { event_type: "THREATEN", goldstein_scale: -7.0, lat: 26.80, lng: 56.60 },
    { event_type: "MILITARY_EXERCISE", goldstein_scale: -3.0, lat: 26.30, lng: 56.00 },
    { event_type: "PROTEST", goldstein_scale: -5.0, lat: 27.19, lng: 56.27 },
    // Cluster 2: Red Sea / Bab el-Mandeb
    { event_type: "USE_FORCE", goldstein_scale: -10.0, lat: 12.65, lng: 43.35 },
    { event_type: "ATTACK", goldstein_scale: -9.4, lat: 13.00, lng: 42.80 },
    // Cluster 3: Eastern Med
    { event_type: "AIRSTRIKE", goldstein_scale: -10.0, lat: 33.30, lng: 35.00 },
    { event_type: "USE_FORCE", goldstein_scale: -8.0, lat: 33.10, lng: 34.60 },
    { event_type: "PROTEST", goldstein_scale: -5.0, lat: 33.80, lng: 35.50 },
    // Cluster 4: South China Sea
    { event_type: "NAVAL_BLOCKADE", goldstein_scale: -8.0, lat: 10.50, lng: 114.00 },
    { event_type: "MILITARY_EXERCISE", goldstein_scale: -4.0, lat: 10.00, lng: 114.50 },
    // Cluster 5: Black Sea
    { event_type: "USE_FORCE", goldstein_scale: -10.0, lat: 44.30, lng: 33.80 },
    { event_type: "ATTACK", goldstein_scale: -9.0, lat: 44.60, lng: 34.20 },
  ],

  gps_jamming: [
    // Cluster 1: Hormuz
    { lat: 26.55, lng: 56.20, radius: 80 },
    // Cluster 2: Red Sea
    { lat: 12.58, lng: 43.32, radius: 60 },
    // Cluster 3: Eastern Med
    { lat: 33.40, lng: 35.10, radius: 50 },
    // Cluster 5: Black Sea
    { lat: 44.40, lng: 33.90, radius: 120 },
    { lat: 44.70, lng: 34.30, radius: 90 },
  ],

  fires: [
    // Cluster 1: Hormuz — possible flaring
    { lat: 26.48, lng: 56.15, brightness: 340 },
    { lat: 26.62, lng: 56.45, brightness: 315 },
    // Cluster 2: Red Sea / Djibouti
    { lat: 12.50, lng: 43.20, brightness: 310 },
    // Cluster 3: Eastern Med — conflict fires
    { lat: 33.25, lng: 34.90, brightness: 380 },
    { lat: 33.60, lng: 35.30, brightness: 350 },
    // Cluster 5: Black Sea — conflict fires
    { lat: 44.20, lng: 34.10, brightness: 400 },
    { lat: 44.55, lng: 33.70, brightness: 370 },
  ],

  ships: [
    // Cluster 1: Hormuz
    { name: "PACIFIC VOYAGER", type: "tanker", flag: "MH", lat: 26.56, lng: 56.25 },
    { name: "STENA IMPERO", type: "tanker", flag: "GB", lat: 26.58, lng: 56.30 },
    { name: "USS EISENHOWER", type: "carrier", flag: "US", lat: 26.65, lng: 56.40 },
    // Cluster 2: Red Sea
    { name: "GALAXY LEADER", type: "car_carrier", flag: "BS", lat: 12.60, lng: 43.30 },
    { name: "USS GRAVELY", type: "military_vessel", flag: "US", lat: 12.58, lng: 43.28 },
    // Cluster 3: Eastern Med
    { name: "INS MAGEN", type: "military_vessel", flag: "IL", lat: 33.15, lng: 34.70 },
    // Cluster 4: South China Sea
    { name: "LIAONING", type: "carrier", flag: "CN", lat: 10.30, lng: 114.20 },
    { name: "SHANDONG", type: "carrier", flag: "CN", lat: 10.10, lng: 114.60 },
    // Cluster 5: Black Sea
    { name: "MOSKVA II", type: "military_vessel", flag: "RU", lat: 44.45, lng: 33.85 },
  ],
};

/** Standardized dataset catalog for the artifacts showcase. */
export const DATASETS = [
  { key: "default", label: "5 CONVERGENCE CLUSTERS", data: DUMMY_CONVERGENCE_DATA },
] as const;
