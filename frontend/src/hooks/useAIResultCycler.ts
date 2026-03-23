import { useState, useCallback, useRef } from "react";
import type { DashboardData, SelectedEntity } from "@/types/dashboard";
import { toSelectedEntity } from "./useCategoryCycler";

/** Entity type → data key mapping for lookup */
const TYPE_TO_DATA_KEY: Record<string, string> = {
  commercial_flight: "commercial_flights",
  private_flight: "private_flights",
  private_jet: "private_jets",
  military_flight: "military_flights",
  tracked_flight: "tracked_flights",
  satellite: "satellites",
  ship: "ships",
  earthquake: "earthquakes",
  cctv: "cctv",
  gdelt_incident: "gdelt",
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
  const dataKey = TYPE_TO_DATA_KEY[type];
  if (!dataKey) return null;

  const items = (data as any)[dataKey];
  if (!Array.isArray(items)) return null;

  const idStr = String(id);
  const match = items.find((item: any) => {
    const itemId = item.icao24 || item.mmsi || item.id || item.name;
    return String(itemId) === idStr;
  });

  return match ? { item: match, entityType: type } : null;
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
          idSet.add(`${type}:${String(selected.id)}`);
        }
      }

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
