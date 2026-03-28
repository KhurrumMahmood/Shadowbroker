import { describe, it, expect } from "vitest";
import { inBounds, computeViewportCounts } from "@/utils/viewportFilter";

const BOUNDS = { south: 30, west: -10, north: 50, east: 30 };

describe("inBounds", () => {
  it("returns true for entity inside bounds", () => {
    expect(inBounds({ lat: 40, lng: 10 }, BOUNDS)).toBe(true);
  });

  it("returns false for entity outside bounds (north)", () => {
    expect(inBounds({ lat: 55, lng: 10 }, BOUNDS)).toBe(false);
  });

  it("returns false for entity outside bounds (east)", () => {
    expect(inBounds({ lat: 40, lng: 35 }, BOUNDS)).toBe(false);
  });

  it("returns true for entity on the boundary edge", () => {
    expect(inBounds({ lat: 30, lng: -10 }, BOUNDS)).toBe(true);
  });

  it("returns false for entity with null lat", () => {
    expect(inBounds({ lat: null, lng: 10 }, BOUNDS)).toBe(false);
  });

  it("returns false for entity with undefined lng", () => {
    expect(inBounds({ lat: 40 }, BOUNDS)).toBe(false);
  });

  it("handles antimeridian wrap (west > east)", () => {
    const wrapBounds = { south: 30, west: 170, north: 50, east: -170 };
    // 175 is between 170 and 180, so it's inside the wrap
    expect(inBounds({ lat: 40, lng: 175 }, wrapBounds)).toBe(true);
    // -175 is between -180 and -170, so it's inside the wrap
    expect(inBounds({ lat: 40, lng: -175 }, wrapBounds)).toBe(true);
    // 0 is outside the wrap
    expect(inBounds({ lat: 40, lng: 0 }, wrapBounds)).toBe(false);
  });
});

const MOCK_DATA = {
  commercial_flights: [
    { icao24: "A1", lat: 40, lng: 10 },
    { icao24: "A2", lat: 60, lng: 10 },   // outside
    { icao24: "A3", lat: 35, lng: 5 },
  ],
  private_flights: [
    { icao24: "P1", lat: 45, lng: 20 },
  ],
  private_jets: [],
  military_flights: [
    { icao24: "M1", lat: 31, lng: 0 },
    { icao24: "M2", lat: 10, lng: 0 },    // outside
  ],
  tracked_flights: [
    { icao24: "T1", lat: 49, lng: 29 },
  ],
  ships: [
    { mmsi: "S1", lat: 40, lng: 10, type: "carrier", yacht_alert: false },
    { mmsi: "S2", lat: 35, lng: 5, type: "cargo", yacht_alert: false },
    { mmsi: "S3", lat: 60, lng: 10, type: "military_vessel", yacht_alert: false },  // outside
    { mmsi: "S4", lat: 45, lng: 15, type: "passenger", yacht_alert: false },
    { mmsi: "S5", lat: 42, lng: 12, type: "civilian", yacht_alert: false },
    { mmsi: "S6", lat: 38, lng: 8, type: "tanker", yacht_alert: true },
  ],
  satellites: [
    { id: "SAT1", lat: 40, lng: 10 },
    { id: "SAT2", lat: 80, lng: 10 },     // outside
  ],
  earthquakes: [
    { id: "EQ1", lat: 35, lng: 5 },
  ],
  firms_fires: [
    { lat: 40, lng: 10 },
    { lat: 70, lng: 10 },                 // outside
  ],
  gdelt: [
    { properties: { lat: 40, lng: 10 } },
    { properties: { lat: 60, lng: 10 } }, // outside
  ],
  gps_jamming: [
    { lat: 45, lng: 20 },
  ],
  cctv: [
    { lat: 40, lng: 10 },
    { lat: 80, lng: 90 },                 // outside
  ],
  kiwisdr: [
    { lat: 35, lng: 5, lon: 5 },
  ],
  meshtastic: [
    { lat: 40, lng: 10 },
  ],
  prediction_markets: [],
  ukraine_alerts: [],
  fimi: [],
  trains: [
    { lat: 40, lng: 10 },
    { lat: 0, lng: 0 },                   // outside
  ],
  internet_outages: [],
  datacenters: [
    { lat: 40, lng: 10 },
  ],
  military_bases: [
    { lat: 35, lng: 5 },
    { lat: 80, lng: 80 },                 // outside
  ],
  power_plants: [
    { lat: 40, lng: 10 },
  ],
  disease_outbreaks: [],
};

describe("computeViewportCounts", () => {
  const counts = computeViewportCounts(MOCK_DATA as any, BOUNDS);

  it("filters commercial flights by viewport", () => {
    expect(counts.flights).toBe(2);         // A1, A3 inside
  });

  it("filters private flights by viewport", () => {
    expect(counts.private).toBe(1);
  });

  it("filters military flights by viewport", () => {
    expect(counts.military).toBe(1);        // M1 inside, M2 outside
  });

  it("filters tracked flights by viewport", () => {
    expect(counts.tracked).toBe(1);
  });

  it("filters military ships by viewport", () => {
    expect(counts.ships_military).toBe(1);  // S1 inside, S3 outside
  });

  it("filters cargo/tanker ships by viewport", () => {
    expect(counts.ships_cargo).toBe(1);     // S2 inside (cargo)
  });

  it("filters passenger ships by viewport", () => {
    expect(counts.ships_passenger).toBe(1);
  });

  it("filters civilian ships by viewport", () => {
    expect(counts.ships_civilian).toBe(1);
  });

  it("filters tracked yachts by viewport", () => {
    expect(counts.ships_tracked_yachts).toBe(1); // S6 yacht_alert inside
  });

  it("filters satellites by viewport", () => {
    expect(counts.satellites).toBe(1);
  });

  it("filters earthquakes by viewport", () => {
    expect(counts.earthquakes).toBe(1);
  });

  it("filters fire hotspots by viewport", () => {
    expect(counts.firms).toBe(1);
  });

  it("filters GDELT incidents by viewport", () => {
    expect(counts.global_incidents).toBe(1);
  });

  it("filters GPS jamming by viewport", () => {
    expect(counts.gps_jamming).toBe(1);
  });

  it("filters CCTV by viewport", () => {
    expect(counts.cctv).toBe(1);
  });

  it("filters trains by viewport", () => {
    expect(counts.trains).toBe(1);
  });

  it("filters datacenters by viewport", () => {
    expect(counts.datacenters).toBe(1);
  });

  it("filters military bases by viewport", () => {
    expect(counts.military_bases).toBe(1);
  });

  it("filters power plants by viewport", () => {
    expect(counts.power_plants).toBe(1);
  });

  it("returns 0 for empty arrays", () => {
    expect(counts.jets).toBe(0);
    expect(counts.prediction_markets).toBe(0);
  });
});
