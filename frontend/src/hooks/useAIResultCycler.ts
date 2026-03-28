import { useState, useCallback, useRef } from "react";
import type { DashboardData, SelectedEntity } from "@/types/dashboard";
import { toSelectedEntity } from "./useCategoryCycler";

/** Normalize entity types the LLM might return in non-canonical forms.
 *  Covers: singular aliases, plural/category-key forms (what the LLM sees as
 *  data section headers), and backend _SEARCH_CONFIG entity_type strings. */
const TYPE_ALIASES: Record<string, string> = {
  // Singular aliases
  military: "military_flight",
  commercial: "flight",
  commercial_flight: "flight",
  tracked: "tracked_flight",
  private: "private_flight",
  jet: "private_jet",
  base: "military_base",
  fire: "firms_fire",
  outage: "internet_outage",
  meshtastic: "meshtastic_node",
  fimi: "fimi_narrative",
  // Plural / category-key forms (LLM sees these as section headers)
  commercial_flights: "flight",
  military_flights: "military_flight",
  tracked_flights: "tracked_flight",
  private_flights: "private_flight",
  private_jets: "private_jet",
  ships: "ship",
  satellites: "satellite",
  earthquakes: "earthquake",
  firms_fires: "firms_fire",
  internet_outages: "internet_outage",
  datacenters: "datacenter",
  military_bases: "military_base",
  power_plants: "power_plant",
  cctv_cameras: "cctv",
  kiwisdr_receivers: "kiwisdr",
  meshtastic_nodes: "meshtastic_node",
  prediction_markets: "prediction_market",
  ukraine_alerts: "ukraine_alert",
  disease_outbreaks: "disease_outbreak",
  trains: "train",
  fimi_narratives: "fimi_narrative",
  correlation_alerts: "correlation",
  correlations: "correlation",
  gdelt_incidents: "gdelt_incident",
  news_articles: "news",
  uavs: "uav",
};

/** Entity type → DashboardData key mapping for lookup */
const TYPE_TO_DATA_KEY: Record<string, string> = {
  flight: "commercial_flights",
  private_flight: "private_flights",
  private_jet: "private_jets",
  military_flight: "military_flights",
  tracked_flight: "tracked_flights",
  satellite: "satellites",
  ship: "ships",
  earthquake: "earthquakes",
  cctv: "cctv",
  gdelt: "gdelt",
  kiwisdr: "kiwisdr",
  firms_fire: "firms_fires",
  internet_outage: "internet_outages",
  datacenter: "datacenters",
  military_base: "military_bases",
  power_plant: "power_plants",
  // Types that exist in backend but previously had no frontend mapping
  prediction_market: "prediction_markets",
  ukraine_alert: "ukraine_alerts",
  fimi_narrative: "fimi",
  train: "trains",
  meshtastic_node: "meshtastic",
  correlation: "correlation_alerts",
  disease_outbreak: "disease_outbreaks",
  gdelt_incident: "gdelt",
  news: "news",
  uav: "uavs",
  gps_jamming: "gps_jamming",
};

/** Find a raw entity item in DashboardData by type + id */
export function findEntityInData(
  type: string,
  id: string | number,
  data: DashboardData,
): { item: any; entityType: string } | null {
  const normalizedType = TYPE_ALIASES[type] ?? type;
  const dataKey = TYPE_TO_DATA_KEY[normalizedType];
  if (!dataKey) {
    console.warn(`[AI Results] Unknown entity type "${type}" — no mapping in TYPE_TO_DATA_KEY`);
    return null;
  }

  const items = (data as any)[dataKey];
  if (!Array.isArray(items)) return null;

  // Strip "id:" prefix the LLM may include from search result format
  const idStr = String(id).replace(/^id:/, "").trim().toLowerCase();

  // Parse coordinate ID if it looks like "lat,lng" or "lat-lng"
  const coordMatch = idStr.match(/^([+-]?\d+\.?\d*)[,\-]([+-]?\d+\.?\d*)$/);
  const coordLat = coordMatch ? parseFloat(coordMatch[1]) : NaN;
  const coordLng = coordMatch ? parseFloat(coordMatch[2]) : NaN;
  const hasCoordId = !isNaN(coordLat) && !isNaN(coordLng);

  const match = items.find((item: any) => {
    // Check all common identifier fields (case-insensitive)
    const candidates = [
      item.icao24, item.mmsi, item.id, item.node_id,
      item.slug, item.name, item.title,
      // GDELT GeoJSON: name is nested in properties
      item.properties?.name,
    ];
    if (candidates.some((c) => c != null && String(c).toLowerCase().trim() === idStr)) return true;
    // Coordinate-based fallback — numeric comparison avoids float formatting issues
    if (hasCoordId) {
      if (item.lat != null && item.lng != null && item.lat === coordLat && item.lng === coordLng) return true;
      // GeoJSON coordinate fallback (GDELT features store coords in geometry)
      if (item.geometry?.coordinates) {
        const [gLng, gLat] = item.geometry.coordinates;
        if (gLat === coordLat && gLng === coordLng) return true;
      }
    }
    return false;
  });

  if (!match) {
    console.warn(`[AI Results] Entity ${type}:${id} not found in ${dataKey} (${items.length} items)`);
  }
  return match ? { item: match, entityType: normalizedType } : null;
}

export interface AIResultState {
  active: boolean;
  index: number;
  total: number;
  results: SelectedEntity[];
  resultIdSet: Set<string>;
  requested: number;
  noneResolved: boolean;
}

export function useAIResultCycler(
  data: DashboardData,
  onSelect: (entity: SelectedEntity | null) => void,
  onFlyTo: (lat: number, lng: number, zoom?: number) => void,
) {
  const [results, setResultsState] = useState<SelectedEntity[]>([]);
  const [index, setIndex] = useState(0);
  const [resultIdSet, setResultIdSet] = useState<Set<string>>(new Set());
  const [requested, setRequested] = useState(0);
  const dataRef = useRef(data);
  dataRef.current = data;

  const flyToEntity = useCallback(
    (entity: SelectedEntity) => {
      const lat = entity.extra?.lat ?? entity.extra?.geometry?.coordinates?.[1];
      const lng = entity.extra?.lng ?? entity.extra?.lon ?? entity.extra?.geometry?.coordinates?.[0];
      if (lat != null && lng != null) onFlyTo(lat, lng);
      onSelect(entity);
    },
    [onSelect, onFlyTo],
  );

  const setResults = useCallback(
    (entities: Array<{ type: string; id: string | number }>) => {
      const resolved: SelectedEntity[] = [];
      const idSet = new Set<string>();

      for (const { type, id } of entities) {
        const found = findEntityInData(type, id, dataRef.current);
        if (found) {
          const selected = toSelectedEntity(found.item, found.entityType);
          resolved.push(selected);
          idSet.add(`${found.entityType}:${String(selected.id)}`);
        }
      }

      console.log(`[AI Results] Resolved ${resolved.length}/${entities.length} entities`);

      setResultsState(resolved);
      setResultIdSet(idSet);
      setRequested(entities.length);
      setIndex(0);

      if (resolved.length > 0) {
        flyToEntity(resolved[0]);
      }
    },
    [flyToEntity],
  );

  const resolveAndFly = useCallback(
    (entity: SelectedEntity) => {
      const found = findEntityInData(entity.type, String(entity.id), dataRef.current);
      if (found) {
        flyToEntity(toSelectedEntity(found.item, found.entityType));
      } else {
        flyToEntity(entity); // Fallback to stale if entity left viewport
      }
    },
    [flyToEntity],
  );

  const next = useCallback(() => {
    if (results.length === 0) return;
    const newIdx = (index + 1) % results.length;
    setIndex(newIdx);
    resolveAndFly(results[newIdx]);
  }, [results, index, resolveAndFly]);

  const prev = useCallback(() => {
    if (results.length === 0) return;
    const newIdx = (index - 1 + results.length) % results.length;
    setIndex(newIdx);
    resolveAndFly(results[newIdx]);
  }, [results, index, resolveAndFly]);

  const clear = useCallback(() => {
    setResultsState([]);
    setResultIdSet(new Set());
    setRequested(0);
    setIndex(0);
    onSelect(null);
  }, [onSelect]);

  const state: AIResultState = {
    active: results.length > 0,
    index,
    total: results.length,
    results,
    resultIdSet,
    requested,
    noneResolved: requested > 0 && results.length === 0,
  };

  return { state, setResults, next, prev, clear };
}
