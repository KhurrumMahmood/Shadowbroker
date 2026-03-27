/**
 * Layer display metadata for AI response toggle chips.
 * Short labels and logical groupings for the 23 map layers.
 */

export const LAYER_LABELS: Record<string, string> = {
  flights: "COMMERCIAL",
  private: "PRIVATE",
  jets: "JETS",
  military: "MILITARY",
  tracked: "TRACKED",
  satellites: "SATELLITES",
  ships_military: "MIL SHIPS",
  ships_cargo: "CARGO SHIPS",
  ships_civilian: "CIV SHIPS",
  ships_passenger: "PASSENGER",
  ships_tracked_yachts: "YACHTS",
  earthquakes: "QUAKES",
  cctv: "CCTV",
  ukraine_frontline: "FRONTLINE",
  global_incidents: "INCIDENTS",
  day_night: "DAY/NIGHT",
  gps_jamming: "GPS JAM",
  kiwisdr: "RADIO",
  firms: "FIRES",
  internet_outages: "OUTAGES",
  datacenters: "DATACENTERS",
  military_bases: "BASES",
  power_plants: "POWER",
  prediction_markets: "MARKETS",
  ukraine_alerts: "UA ALERTS",
  fimi: "DISINFO",
  trains: "TRAINS",
  meshtastic: "MESH",
};

export const LAYER_GROUPS: Record<string, { label: string; members: string[] }> = {
  ships: {
    label: "ALL SHIPS",
    members: ["ships_military", "ships_cargo", "ships_civilian", "ships_passenger", "ships_tracked_yachts"],
  },
  flights: {
    label: "ALL FLIGHTS",
    members: ["flights", "private", "jets", "military", "tracked"],
  },
  intel: {
    label: "INTEL",
    members: ["gps_jamming", "satellites", "global_incidents", "military_bases", "prediction_markets", "fimi"],
  },
};
