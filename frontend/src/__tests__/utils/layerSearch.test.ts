import { describe, it, expect } from "vitest";
import { searchEntities, getSearchableText } from "@/utils/layerSearch";

describe("getSearchableText", () => {
  it("extracts flight fields", () => {
    const text = getSearchableText({ callsign: "UAL123", icao24: "abc123", registration: "N12345", airline: "United" });
    expect(text).toContain("UAL123");
    expect(text).toContain("abc123");
    expect(text).toContain("N12345");
    expect(text).toContain("United");
  });

  it("extracts ship fields", () => {
    const text = getSearchableText({ name: "EVER GIVEN", mmsi: "353136000", country: "Panama" });
    expect(text).toContain("EVER GIVEN");
    expect(text).toContain("353136000");
    expect(text).toContain("Panama");
  });

  it("handles entities with minimal fields", () => {
    const text = getSearchableText({ lat: 40, lng: 10 });
    expect(typeof text).toBe("string");
  });

  it("extracts GDELT properties", () => {
    const text = getSearchableText({ title: "Explosion in port", properties: { action_geo_cc: "LB" } });
    expect(text).toContain("Explosion in port");
    expect(text).toContain("LB");
  });
});

describe("searchEntities", () => {
  const items = [
    { callsign: "UAL123", icao24: "abc123", name: "United 123", lat: 40, lng: -74 },
    { callsign: "DAL456", icao24: "def456", name: "Delta 456", lat: 35, lng: -80 },
    { callsign: "SWA789", icao24: "ghi789", name: "Southwest 789", lat: 33, lng: -97 },
    { callsign: "AAL100", icao24: "jkl100", name: "American 100", lat: 39, lng: -77 },
  ];

  it("returns all items when query is empty", () => {
    expect(searchEntities(items, "")).toEqual(items);
  });

  it("returns all items when query is whitespace", () => {
    expect(searchEntities(items, "   ")).toEqual(items);
  });

  it("filters by callsign", () => {
    const results = searchEntities(items, "UAL");
    expect(results).toHaveLength(1);
    expect(results[0].callsign).toBe("UAL123");
  });

  it("filters by name (case insensitive)", () => {
    const results = searchEntities(items, "delta");
    expect(results).toHaveLength(1);
    expect(results[0].callsign).toBe("DAL456");
  });

  it("filters by icao24", () => {
    const results = searchEntities(items, "ghi789");
    expect(results).toHaveLength(1);
    expect(results[0].callsign).toBe("SWA789");
  });

  it("returns multiple matches", () => {
    const results = searchEntities(items, "al");
    // UAL123, DAL456, AAL100 all contain "al"
    expect(results.length).toBeGreaterThanOrEqual(2);
  });

  it("sorts exact matches first", () => {
    const results = searchEntities(items, "UAL123");
    expect(results[0].callsign).toBe("UAL123");
  });

  it("returns empty array when nothing matches", () => {
    const results = searchEntities(items, "ZZZNOTFOUND");
    expect(results).toHaveLength(0);
  });

  it("searches ship MMSI", () => {
    const ships = [
      { name: "EVER GIVEN", mmsi: "353136000", lat: 30, lng: 32 },
      { name: "MAERSK ALABAMA", mmsi: "123456789", lat: 2, lng: 45 },
    ];
    const results = searchEntities(ships, "353136");
    expect(results).toHaveLength(1);
    expect(results[0].name).toBe("EVER GIVEN");
  });

  it("searches satellite names", () => {
    const sats = [
      { name: "ISS (ZARYA)", id: "25544", lat: 51, lng: 0 },
      { name: "STARLINK-1234", id: "99999", lat: 53, lng: -1 },
    ];
    const results = searchEntities(sats, "starlink");
    expect(results).toHaveLength(1);
    expect(results[0].name).toBe("STARLINK-1234");
  });
});
