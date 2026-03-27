/**
 * Dummy data fixture for Entity Risk Dashboard.
 * 8 tracked entities across maritime, aviation, military, and infrastructure.
 * ONLY use when explicitly requested — never in production.
 */

import type { EntityData } from "./EntityRiskDashboard";

export const DUMMY_ENTITY_DATA: EntityData = {
  entities: [
    { name: "EVER GIVEN", domain: "maritime", type: "cargo", risk_level: 7, lat: 30.0, lng: 32.3, summary: "Large container vessel transiting Suez Canal zone" },
    { name: "AF1", domain: "aviation", type: "tracked_aircraft", risk_level: 9, lat: 38.9, lng: -77.0, summary: "VIP government aircraft, restricted airspace active" },
    { name: "USS EISENHOWER", domain: "military", type: "carrier", risk_level: 8, lat: 15.4, lng: 42.1, summary: "Carrier strike group operating in Red Sea theater" },
    { name: "LADY GULYA", domain: "maritime", type: "yacht", risk_level: 5, lat: 43.7, lng: 7.4, summary: "Tracked superyacht moored in Monaco" },
    { name: "RSD052", domain: "aviation", type: "military_aircraft", risk_level: 6, lat: 55.0, lng: 37.6, summary: "Russian military transport, unusual flight path" },
    { name: "LIAONING", domain: "military", type: "carrier", risk_level: 9, lat: 18.2, lng: 114.5, summary: "PLAN carrier operating in South China Sea" },
    { name: "STARLINK-4721", domain: "infrastructure", type: "satellite", risk_level: 2, lat: 0, lng: 0, summary: "LEO satellite, normal orbit parameters" },
    { name: "SEVMORPUT", domain: "maritime", type: "cargo", risk_level: 6, lat: 69.0, lng: 33.0, summary: "Nuclear-powered cargo vessel, Northern Sea Route" },
  ],
};

/** Standardized dataset catalog for the artifacts showcase. */
export const DATASETS = [
  { key: "default", label: "8 TRACKED ENTITIES", data: DUMMY_ENTITY_DATA },
] as const;
