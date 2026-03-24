import { describe, it, expect } from "vitest";
import { findEntityInData } from "@/hooks/useAIResultCycler";
import type { DashboardData } from "@/types/dashboard";

const MOCK_DATA = {
  commercial_flights: [
    { icao24: "abc123", callsign: "BA123", lat: 51.0, lng: -0.5, alt: 35000, origin_name: "LHR" },
    { icao24: "def456", callsign: "AF789", lat: 48.8, lng: 2.3, alt: 38000, origin_name: "CDG" },
  ],
  ships: [
    { mmsi: 222222, name: "FRONT ALTAIR", type: "tanker", lat: 26.5, lng: 56.3 },
    { mmsi: 333333, name: "USS NIMITZ", type: "carrier", lat: 26.6, lng: 56.4 },
  ],
  military_flights: [
    { icao24: "mil001", callsign: "RCH401", lat: 43.0, lng: 34.0, alt: 30000 },
  ],
  military_bases: [
    { name: "Ramstein Air Base", country: "Germany", lat: 49.44, lng: 7.6 },
  ],
  earthquakes: [
    { id: "eq001", place: "Near Tokyo", lat: 35.6, lng: 139.7, mag: 4.2 },
  ],
} as unknown as DashboardData;

describe("findEntityInData", () => {
  it("finds a flight by icao24", () => {
    const found = findEntityInData("flight", "abc123", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("BA123");
    expect(found!.entityType).toBe("flight");
  });

  it("finds a ship by mmsi", () => {
    const found = findEntityInData("ship", 222222, MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.name).toBe("FRONT ALTAIR");
  });

  it("finds a military flight", () => {
    const found = findEntityInData("military_flight", "mil001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("RCH401");
  });

  it("finds a military base by name", () => {
    const found = findEntityInData("military_base", "Ramstein Air Base", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.country).toBe("Germany");
  });

  it("finds an earthquake by id", () => {
    const found = findEntityInData("earthquake", "eq001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.place).toBe("Near Tokyo");
  });

  it("returns null for unknown type", () => {
    const found = findEntityInData("unknown_type", "abc", MOCK_DATA);
    expect(found).toBeNull();
  });

  it("returns null for non-existent id", () => {
    const found = findEntityInData("flight", "nonexistent", MOCK_DATA);
    expect(found).toBeNull();
  });

  it("handles numeric id as string comparison", () => {
    const found = findEntityInData("ship", "333333", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.name).toBe("USS NIMITZ");
  });

  // ── TYPE_ALIASES tests ──

  it("resolves 'military' alias to military_flight", () => {
    const found = findEntityInData("military", "mil001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("RCH401");
    expect(found!.entityType).toBe("military_flight");
  });

  it("resolves 'commercial' alias to flight", () => {
    const found = findEntityInData("commercial", "abc123", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("BA123");
    expect(found!.entityType).toBe("flight");
  });

  it("resolves 'base' alias to military_base", () => {
    const found = findEntityInData("base", "Ramstein Air Base", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.country).toBe("Germany");
    expect(found!.entityType).toBe("military_base");
  });

  // ── id: prefix stripping ──

  it("strips 'id:' prefix from entity id", () => {
    const found = findEntityInData("flight", "id:abc123", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("BA123");
  });

  it("strips 'id:' prefix from numeric id", () => {
    const found = findEntityInData("ship", "id:222222", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.name).toBe("FRONT ALTAIR");
  });

  // ── Re-resolution: fresh data returns updated positions ──

  it("returns updated position when entity has moved", () => {
    const staleData = {
      ...MOCK_DATA,
      commercial_flights: [
        { icao24: "abc123", callsign: "BA123", lat: 51.0, lng: -0.5, alt: 35000, origin_name: "LHR" },
      ],
    } as unknown as DashboardData;

    const freshData = {
      ...MOCK_DATA,
      commercial_flights: [
        { icao24: "abc123", callsign: "BA123", lat: 52.5, lng: 1.2, alt: 36000, origin_name: "LHR" },
      ],
    } as unknown as DashboardData;

    const stale = findEntityInData("flight", "abc123", staleData);
    const fresh = findEntityInData("flight", "abc123", freshData);

    expect(stale!.item.lat).toBe(51.0);
    expect(fresh!.item.lat).toBe(52.5);
    expect(fresh!.item.lng).toBe(1.2);
  });

  it("returns null when entity is no longer in data", () => {
    const emptyData = {
      ...MOCK_DATA,
      commercial_flights: [],
    } as unknown as DashboardData;

    const found = findEntityInData("flight", "abc123", emptyData);
    expect(found).toBeNull();
  });
});
