import { useState, useCallback, useMemo } from "react";
import type { DashboardData, SelectedEntity } from "@/types/dashboard";

/** Maps a layer ID to its entity array + entity-type string for SelectedEntity */
function getEntities(layerId: string, data: DashboardData): { items: any[]; entityType: string } {
  switch (layerId) {
    case "flights":
      return { items: data.commercial_flights ?? [], entityType: "commercial_flight" };
    case "private":
      return { items: data.private_flights ?? [], entityType: "private_flight" };
    case "jets":
      return { items: data.private_jets ?? [], entityType: "private_jet" };
    case "military":
      return { items: data.military_flights ?? [], entityType: "military_flight" };
    case "tracked":
      return { items: data.tracked_flights ?? [], entityType: "tracked_flight" };
    case "satellites":
      return { items: data.satellites ?? [], entityType: "satellite" };
    case "ships_military":
      return {
        items: (data.ships ?? []).filter(s => s.type === "carrier" || s.type === "military_vessel"),
        entityType: "ship",
      };
    case "ships_cargo":
      return {
        items: (data.ships ?? []).filter(s => s.type === "tanker" || s.type === "cargo"),
        entityType: "ship",
      };
    case "ships_civilian":
      return {
        items: (data.ships ?? []).filter(s =>
          !s.yacht_alert && s.type !== "carrier" && s.type !== "military_vessel" &&
          s.type !== "tanker" && s.type !== "cargo" && s.type !== "passenger"
        ),
        entityType: "ship",
      };
    case "ships_passenger":
      return {
        items: (data.ships ?? []).filter(s => s.type === "passenger"),
        entityType: "ship",
      };
    case "ships_tracked_yachts":
      return {
        items: (data.ships ?? []).filter(s => s.yacht_alert),
        entityType: "ship",
      };
    case "earthquakes":
      return { items: data.earthquakes ?? [], entityType: "earthquake" };
    case "cctv":
      return { items: data.cctv ?? [], entityType: "cctv" };
    case "global_incidents":
      return { items: data.gdelt ?? [], entityType: "gdelt_incident" };
    case "kiwisdr":
      return { items: data.kiwisdr ?? [], entityType: "kiwisdr" };
    case "firms":
      return { items: data.firms_fires ?? [], entityType: "firms_fire" };
    case "internet_outages":
      return { items: data.internet_outages ?? [], entityType: "internet_outage" };
    case "datacenters":
      return { items: data.datacenters ?? [], entityType: "datacenter" };
    case "military_bases":
      return { items: data.military_bases ?? [], entityType: "military_base" };
    case "power_plants":
      return { items: data.power_plants ?? [], entityType: "power_plant" };
    default:
      return { items: [], entityType: "" };
  }
}

/** Build a SelectedEntity from a raw data item + entity type */
function toSelectedEntity(item: any, entityType: string): SelectedEntity {
  const id = item.icao24 || item.mmsi || item.id || item.name || `${item.lat}-${item.lng}`;
  const name =
    item.callsign || item.name || item.tracked_name || item.yacht_name ||
    item.place || item.title || item.region_name || item.company || "";
  return { id, type: entityType, name, extra: item };
}

export interface CyclerState {
  active: boolean;
  layerId: string | null;
  index: number;
  total: number;
}

export function useCategoryCycler(
  data: DashboardData,
  onSelect: (entity: SelectedEntity | null) => void,
  onFlyTo: (lat: number, lng: number) => void,
) {
  const [activeLayer, setActiveLayer] = useState<string | null>(null);
  const [index, setIndex] = useState(0);

  const entities = useMemo(() => {
    if (!activeLayer) return { items: [], entityType: "" };
    return getEntities(activeLayer, data);
  }, [activeLayer, data]);

  const flyToItem = useCallback(
    (item: any, entityType: string) => {
      const lat = item.lat ?? item.geometry?.coordinates?.[1];
      const lng = item.lng ?? item.lon ?? item.geometry?.coordinates?.[0];
      if (lat != null && lng != null) onFlyTo(lat, lng);
      onSelect(toSelectedEntity(item, entityType));
    },
    [onSelect, onFlyTo],
  );

  const startCycling = useCallback(
    (layerId: string) => {
      if (activeLayer === layerId) {
        // Toggle off
        setActiveLayer(null);
        setIndex(0);
        onSelect(null);
        return;
      }
      const { items, entityType } = getEntities(layerId, data);
      setActiveLayer(layerId);
      setIndex(0);
      if (items.length > 0) flyToItem(items[0], entityType);
    },
    [activeLayer, data, flyToItem, onSelect],
  );

  const next = useCallback(() => {
    if (!activeLayer || entities.items.length === 0) return;
    const newIdx = (index + 1) % entities.items.length;
    setIndex(newIdx);
    flyToItem(entities.items[newIdx], entities.entityType);
  }, [activeLayer, entities, index, flyToItem]);

  const prev = useCallback(() => {
    if (!activeLayer || entities.items.length === 0) return;
    const newIdx = (index - 1 + entities.items.length) % entities.items.length;
    setIndex(newIdx);
    flyToItem(entities.items[newIdx], entities.entityType);
  }, [activeLayer, entities, index, flyToItem]);

  const stop = useCallback(() => {
    setActiveLayer(null);
    setIndex(0);
    onSelect(null);
  }, [onSelect]);

  const state: CyclerState = {
    active: activeLayer !== null,
    layerId: activeLayer,
    index,
    total: entities.items.length,
  };

  return { state, startCycling, next, prev, stop };
}
