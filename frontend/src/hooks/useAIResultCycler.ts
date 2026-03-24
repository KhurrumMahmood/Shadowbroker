import { useState, useCallback, useRef } from "react";
import type { DashboardData, SelectedEntity } from "@/types/dashboard";
import { toSelectedEntity } from "./useCategoryCycler";

/** Normalize entity types the LLM might return in non-canonical forms */
const TYPE_ALIASES: Record<string, string> = {
  military: "military_flight",
  commercial: "flight",
  commercial_flight: "flight",
  private: "private_flight",
  jet: "private_jet",
  base: "military_base",
  fire: "firms_fire",
  outage: "internet_outage",
};

/** Entity type → data key mapping for lookup */
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
  const idStr = String(id).replace(/^id:/, "");
  const match = items.find((item: any) => {
    const itemId = item.icao24 || item.mmsi || item.id || item.name;
    return String(itemId) === idStr;
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
}

export function useAIResultCycler(
  data: DashboardData,
  onSelect: (entity: SelectedEntity | null) => void,
  onFlyTo: (lat: number, lng: number, zoom?: number) => void,
) {
  const [results, setResultsState] = useState<SelectedEntity[]>([]);
  const [index, setIndex] = useState(0);
  const [resultIdSet, setResultIdSet] = useState<Set<string>>(new Set());
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
      setIndex(0);

      if (resolved.length > 0) {
        flyToEntity(resolved[0]);
      }
    },
    [flyToEntity],
  );

  const next = useCallback(() => {
    if (results.length === 0) return;
    const newIdx = (index + 1) % results.length;
    setIndex(newIdx);
    flyToEntity(results[newIdx]);
  }, [results, index, flyToEntity]);

  const prev = useCallback(() => {
    if (results.length === 0) return;
    const newIdx = (index - 1 + results.length) % results.length;
    setIndex(newIdx);
    flyToEntity(results[newIdx]);
  }, [results, index, flyToEntity]);

  const clear = useCallback(() => {
    setResultsState([]);
    setResultIdSet(new Set());
    setIndex(0);
    onSelect(null);
  }, [onSelect]);

  const state: AIResultState = {
    active: results.length > 0,
    index,
    total: results.length,
    results,
    resultIdSet,
  };

  return { state, setResults, next, prev, clear };
}
