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
  tracked_flights: [
    { icao24: "trk001", callsign: "DUKE01", lat: 38.0, lng: -77.0, alt: 25000 },
  ],
  military_bases: [
    { name: "Ramstein Air Base", country: "Germany", lat: 49.44, lng: 7.6 },
  ],
  earthquakes: [
    { id: "eq001", place: "Near Tokyo", lat: 35.6, lng: 139.7, mag: 4.2 },
  ],
  satellites: [
    { id: "sat001", name: "ISS", lat: 51.6, lng: -0.1 },
  ],
  prediction_markets: [
    { id: "pm001", title: "Will X happen?", slug: "will-x-happen", lat: 40.7, lng: -74.0 },
  ],
  ukraine_alerts: [
    { id: "ua001", title: "Air raid Kyiv", lat: 50.4, lng: 30.5 },
  ],
  fimi: [
    { id: "fimi001", title: "Disinfo Campaign Alpha", lat: 48.8, lng: 2.3 },
  ],
  trains: [
    { id: "train001", name: "Eurostar 9001", lat: 51.5, lng: -0.1 },
  ],
  meshtastic: [
    { node_id: "mesh001", name: "Node Alpha", lat: 37.7, lng: -122.4 },
  ],
  disease_outbreaks: [
    { id: "dis001", title: "H5N1 Cluster", lat: 13.7, lng: 100.5 },
  ],
  correlation_alerts: [
    { id: "corr001", title: "Ship-Flight Convergence", lat: 26.5, lng: 56.3 },
  ],
  gdelt: [
    { id: "gdelt001", title: "Protest in capital", lat: 38.9, lng: -77.0 },
  ],
  news: [
    { id: "news001", title: "Breaking: Major Event", lat: 51.5, lng: -0.1 },
  ],
  uavs: [
    { icao24: "uav001", callsign: "DRONE1", lat: 34.0, lng: -118.0 },
  ],
  firms_fires: [
    { lat: 34.05, lng: -118.25, frp: 50, brightness: 320 },
  ],
  gps_jamming: [
    { lat: 26.5, lng: 56.3, radius_km: 50, source: "unknown" },
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

  // ── Plural / category-key type resolution (LLM sends data-key names) ──

  it("resolves plural 'commercial_flights' to flight", () => {
    const found = findEntityInData("commercial_flights", "abc123", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("BA123");
    expect(found!.entityType).toBe("flight");
  });

  it("resolves plural 'military_flights' to military_flight", () => {
    const found = findEntityInData("military_flights", "mil001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("RCH401");
    expect(found!.entityType).toBe("military_flight");
  });

  it("resolves plural 'tracked_flights' to tracked_flight", () => {
    const found = findEntityInData("tracked_flights", "trk001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("DUKE01");
  });

  it("resolves plural 'ships' to ship", () => {
    const found = findEntityInData("ships", 222222, MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.name).toBe("FRONT ALTAIR");
    expect(found!.entityType).toBe("ship");
  });

  it("resolves plural 'satellites' to satellite", () => {
    const found = findEntityInData("satellites", "sat001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.name).toBe("ISS");
  });

  it("resolves plural 'earthquakes' to earthquake", () => {
    const found = findEntityInData("earthquakes", "eq001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.place).toBe("Near Tokyo");
  });

  it("resolves plural 'military_bases' to military_base", () => {
    const found = findEntityInData("military_bases", "Ramstein Air Base", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.entityType).toBe("military_base");
  });

  it("resolves plural 'firms_fires' to firms_fire", () => {
    const found = findEntityInData("firms_fires", "34.05--118.25", MOCK_DATA);
    expect(found).not.toBeNull();
  });

  it("resolves plural 'datacenters' to datacenter", () => {
    const mockWithDC = {
      ...MOCK_DATA,
      datacenters: [{ id: "dc001", name: "AWS us-east-1", lat: 39.0, lng: -77.5 }],
    } as unknown as DashboardData;
    const found = findEntityInData("datacenters", "dc001", mockWithDC);
    expect(found).not.toBeNull();
    expect(found!.entityType).toBe("datacenter");
  });

  it("resolves plural 'power_plants' to power_plant", () => {
    const mockWithPP = {
      ...MOCK_DATA,
      power_plants: [{ id: "pp001", name: "Three Gorges Dam", lat: 30.8, lng: 111.0 }],
    } as unknown as DashboardData;
    const found = findEntityInData("power_plants", "pp001", mockWithPP);
    expect(found).not.toBeNull();
    expect(found!.entityType).toBe("power_plant");
  });

  // ── Missing entity types that exist in backend but had no frontend mapping ──

  it("resolves 'prediction_market' type", () => {
    const found = findEntityInData("prediction_market", "pm001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.title).toBe("Will X happen?");
  });

  it("resolves 'ukraine_alert' type", () => {
    const found = findEntityInData("ukraine_alert", "ua001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.title).toBe("Air raid Kyiv");
  });

  it("resolves 'fimi_narrative' type", () => {
    const found = findEntityInData("fimi_narrative", "fimi001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.title).toBe("Disinfo Campaign Alpha");
  });

  it("resolves 'train' type", () => {
    const found = findEntityInData("train", "train001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.name).toBe("Eurostar 9001");
  });

  it("resolves 'meshtastic_node' type", () => {
    const found = findEntityInData("meshtastic_node", "mesh001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.name).toBe("Node Alpha");
  });

  it("resolves 'meshtastic' shorthand to meshtastic_node", () => {
    const found = findEntityInData("meshtastic", "mesh001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.entityType).toBe("meshtastic_node");
  });

  it("resolves 'correlation' type", () => {
    const found = findEntityInData("correlation", "corr001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.title).toBe("Ship-Flight Convergence");
  });

  it("resolves 'disease_outbreak' type", () => {
    const found = findEntityInData("disease_outbreak", "dis001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.title).toBe("H5N1 Cluster");
  });

  it("resolves 'gdelt_incident' type", () => {
    const found = findEntityInData("gdelt_incident", "gdelt001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.title).toBe("Protest in capital");
  });

  it("resolves 'news' type", () => {
    const found = findEntityInData("news", "news001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.title).toBe("Breaking: Major Event");
  });

  it("resolves 'uav' type", () => {
    const found = findEntityInData("uav", "uav001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("DRONE1");
  });

  it("resolves plural 'uavs' to uav", () => {
    const found = findEntityInData("uavs", "uav001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.entityType).toBe("uav");
  });

  // ── Coordinate-based fallback for entities with no stable ID ──

  it("matches fire hotspot by lat-lng coordinate ID", () => {
    const found = findEntityInData("firms_fire", "34.05--118.25", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.frp).toBe(50);
  });

  it("matches GPS jamming zone by lat-lng coordinate ID", () => {
    const found = findEntityInData("gps_jamming", "26.5-56.3", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.radius_km).toBe(50);
  });

  // ── node_id field matching ──

  it("matches meshtastic node by node_id field", () => {
    const found = findEntityInData("meshtastic_node", "mesh001", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.node_id).toBe("mesh001");
  });

  // ── slug field matching ──

  it("matches prediction market by slug", () => {
    const found = findEntityInData("prediction_market", "will-x-happen", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.title).toBe("Will X happen?");
  });

  // ── title field matching ──

  it("matches entity by title when no other ID field matches", () => {
    const found = findEntityInData("fimi_narrative", "Disinfo Campaign Alpha", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.id).toBe("fimi001");
  });

  // ── Coordinate comma format (backend sends "lat,lng") ──

  it("matches fire by comma-separated coordinate ID", () => {
    const found = findEntityInData("fire", "34.05,-118.25", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.frp).toBe(50);
  });

  it("matches GPS jamming by comma-separated coordinate ID", () => {
    const found = findEntityInData("gps_jamming", "26.5,56.3", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.radius_km).toBe(50);
  });

  it("strips id: prefix from comma coordinate ID", () => {
    const found = findEntityInData("fire", "id:34.05,-118.25", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.frp).toBe(50);
  });

  // ── Case-insensitive matching ──

  it("matches ship name case-insensitively", () => {
    const found = findEntityInData("ship", "front altair", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.mmsi).toBe(222222);
  });

  it("matches flight icao24 case-insensitively", () => {
    const found = findEntityInData("flight", "ABC123", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("BA123");
  });

  it("trims whitespace from entity ID", () => {
    const found = findEntityInData("flight", "  abc123  ", MOCK_DATA);
    expect(found).not.toBeNull();
    expect(found!.item.callsign).toBe("BA123");
  });

  // ── GeoJSON coordinate fallback (GDELT) ──

  it("matches GDELT GeoJSON feature by coordinate ID", () => {
    const geoData = {
      ...MOCK_DATA,
      gdelt: [{
        type: "Feature",
        properties: { name: "Sudan conflict zone", count: 15, action_geo_cc: "SD" },
        geometry: { type: "Point", coordinates: [32.0, 15.0] },
      }],
    } as unknown as DashboardData;
    const found = findEntityInData("gdelt_incident", "15.0,32.0", geoData);
    expect(found).not.toBeNull();
    expect(found!.item.properties.name).toBe("Sudan conflict zone");
  });

  it("matches GDELT GeoJSON feature by properties.name", () => {
    const geoData = {
      ...MOCK_DATA,
      gdelt: [{
        type: "Feature",
        properties: { name: "Sudan conflict zone", count: 15, action_geo_cc: "SD" },
        geometry: { type: "Point", coordinates: [32.0, 15.0] },
      }],
    } as unknown as DashboardData;
    const found = findEntityInData("gdelt_incident", "Sudan conflict zone", geoData);
    expect(found).not.toBeNull();
    expect(found!.item.properties.name).toBe("Sudan conflict zone");
  });
});
