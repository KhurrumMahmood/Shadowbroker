import type { DashboardData } from "@/types/dashboard";

export type ShipCategory = "military" | "cargo" | "passenger" | "civilian" | "yacht";

/** Classify a ship into one of the 5 dashboard categories. */
export function classifyShipCategory(ship: { yacht_alert?: boolean; type?: string }): ShipCategory {
  if (ship.yacht_alert) return "yacht";
  const t = ship.type;
  if (t === "carrier" || t === "military_vessel") return "military";
  if (t === "tanker" || t === "cargo") return "cargo";
  if (t === "passenger") return "passenger";
  return "civilian";
}

export type ViewBounds = {
  south: number;
  west: number;
  north: number;
  east: number;
};

/** Check if an entity (anything with lat/lng) falls inside the given bounds. */
export function inBounds(
  entity: { lat?: number | null; lng?: number | null; [key: string]: any },
  bounds: ViewBounds,
): boolean {
  const { lat, lng } = entity;
  if (lat == null || lng == null) return false;

  if (lat < bounds.south || lat > bounds.north) return false;

  // Handle antimeridian wrap: when west > east, the bbox crosses the 180° line
  if (bounds.west <= bounds.east) {
    return lng >= bounds.west && lng <= bounds.east;
  }
  // Wrapped: entity is inside if it's east of west OR west of east
  return lng >= bounds.west || lng <= bounds.east;
}

/** Count entities per layer that fall inside the viewport bounds. */
export function computeViewportCounts(
  data: DashboardData,
  bounds: ViewBounds,
): Record<string, number> {
  const count = (items: any[] | undefined | null): number => {
    if (!items) return 0;
    let n = 0;
    for (const e of items) if (inBounds(e, bounds)) n++;
    return n;
  };

  // GDELT items store coords inside .properties
  const countGdelt = (items: any[] | undefined | null): number => {
    if (!items) return 0;
    let n = 0;
    for (const e of items) if (inBounds(e.properties ?? e, bounds)) n++;
    return n;
  };

  // Ships need per-type breakdown
  const ships = data?.ships ?? [];
  let shipsMilitary = 0,
    shipsCargo = 0,
    shipsPassenger = 0,
    shipsCivilian = 0,
    shipsYacht = 0;
  for (const s of ships) {
    if (!inBounds(s, bounds)) continue;
    switch (classifyShipCategory(s)) {
      case "military": shipsMilitary++; break;
      case "cargo": shipsCargo++; break;
      case "passenger": shipsPassenger++; break;
      case "yacht": shipsYacht++; break;
      default: shipsCivilian++; break;
    }
  }

  return {
    flights: count(data?.commercial_flights),
    private: count(data?.private_flights),
    jets: count(data?.private_jets),
    military: count(data?.military_flights),
    tracked: count(data?.tracked_flights),
    ships_military: shipsMilitary,
    ships_cargo: shipsCargo,
    ships_passenger: shipsPassenger,
    ships_civilian: shipsCivilian,
    ships_tracked_yachts: shipsYacht,
    satellites: count(data?.satellites),
    earthquakes: count(data?.earthquakes),
    firms: count(data?.firms_fires),
    global_incidents: countGdelt(data?.gdelt),
    gps_jamming: count(data?.gps_jamming),
    cctv: count(data?.cctv),
    kiwisdr: count(data?.kiwisdr),
    meshtastic: count(data?.meshtastic),
    prediction_markets: count(data?.prediction_markets),
    ukraine_alerts: count(data?.ukraine_alerts),
    fimi: count(data?.fimi),
    trains: count(data?.trains),
    internet_outages: count(data?.internet_outages),
    datacenters: count(data?.datacenters),
    military_bases: count(data?.military_bases),
    power_plants: count(data?.power_plants),
  };
}
