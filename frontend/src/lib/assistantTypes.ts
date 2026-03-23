/** Known layer keys the frontend can toggle */
const VALID_LAYERS = new Set([
  "flights", "private", "jets", "military", "tracked", "satellites",
  "ships_military", "ships_cargo", "ships_civilian", "ships_passenger",
  "ships_tracked_yachts", "earthquakes", "cctv", "ukraine_frontline",
  "global_incidents", "day_night", "gps_jamming", "kiwisdr", "firms",
  "internet_outages", "datacenters", "military_bases", "power_plants",
]);

/** Known filter keys the frontend supports */
const VALID_FILTERS = new Set([
  "commercial_departure", "commercial_arrival", "commercial_airline",
  "private_callsign", "private_aircraft_type",
  "military_country", "military_aircraft_type",
  "tracked_category", "tracked_owner",
  "ship_name", "ship_type",
]);

export interface AssistantResponse {
  summary: string;
  layers: Record<string, boolean> | null;
  viewport: { lat: number; lng: number; zoom: number } | null;
  highlight_entities: Array<{ type: string; id: string | number }>;
  result_entities: Array<{ type: string; id: string | number }>;
  filters: Record<string, string[]> | null;
}

/**
 * Validate and sanitize an LLM response from the backend.
 * Strips unknown layer keys, clamps viewport to valid ranges,
 * and provides safe defaults for missing fields.
 */
export function validateAssistantResponse(raw: unknown): AssistantResponse {
  if (!raw || typeof raw !== "object") {
    return {
      summary: "Unable to parse assistant response.",
      layers: null,
      viewport: null,
      highlight_entities: [],
      result_entities: [],
      filters: null,
    };
  }

  const obj = raw as Record<string, unknown>;

  // Summary
  const summary = typeof obj.summary === "string" && obj.summary.length > 0
    ? obj.summary
    : "No response from assistant.";

  // Layers — filter to known keys only
  let layers: Record<string, boolean> | null = null;
  if (obj.layers && typeof obj.layers === "object") {
    layers = {};
    for (const [k, v] of Object.entries(obj.layers as Record<string, unknown>)) {
      if (VALID_LAYERS.has(k)) {
        layers[k] = Boolean(v);
      }
    }
    if (Object.keys(layers).length === 0) layers = null;
  }

  // Viewport — clamp ranges
  let viewport: AssistantResponse["viewport"] = null;
  if (obj.viewport && typeof obj.viewport === "object") {
    const vp = obj.viewport as Record<string, unknown>;
    const lat = typeof vp.lat === "number" ? Math.max(-90, Math.min(90, vp.lat)) : null;
    const lng = typeof vp.lng === "number" ? Math.max(-180, Math.min(180, vp.lng)) : null;
    const zoom = typeof vp.zoom === "number" ? Math.max(1, Math.min(20, vp.zoom)) : 5;
    if (lat !== null && lng !== null) {
      viewport = { lat, lng, zoom };
    }
  }

  // Highlight entities
  const highlight_entities: AssistantResponse["highlight_entities"] = [];
  if (Array.isArray(obj.highlight_entities)) {
    for (const e of obj.highlight_entities) {
      if (e && typeof e === "object" && "type" in e && "id" in e) {
        highlight_entities.push({ type: String(e.type), id: e.id });
      }
    }
  }

  // Result entities — max 50
  const result_entities: AssistantResponse["result_entities"] = [];
  if (Array.isArray(obj.result_entities)) {
    for (const e of obj.result_entities.slice(0, 50)) {
      if (e && typeof e === "object" && "type" in e && "id" in e) {
        result_entities.push({ type: String(e.type), id: e.id });
      }
    }
  }

  // Filters — validate keys against known filter set
  let filters: Record<string, string[]> | null = null;
  if (obj.filters && typeof obj.filters === "object") {
    filters = {};
    for (const [k, v] of Object.entries(obj.filters as Record<string, unknown>)) {
      if (VALID_FILTERS.has(k) && Array.isArray(v)) {
        filters[k] = v.map(String);
      }
    }
    // {} means "clear all filters" — preserve it as distinct from null ("no change")
  }

  return { summary, layers, viewport, highlight_entities, result_entities, filters };
}
