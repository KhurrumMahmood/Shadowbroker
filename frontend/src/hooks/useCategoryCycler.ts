import { useState, useCallback, useMemo } from "react";
import type { DashboardData, SelectedEntity } from "@/types/dashboard";

/** Maps a layer ID to its entity array + entity-type string for SelectedEntity */
export function getEntities(layerId: string, data: DashboardData): { items: any[]; entityType: string } {
  switch (layerId) {
    case "flights":
      return { items: data.commercial_flights ?? [], entityType: "flight" };
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
      return { items: data.gdelt ?? [], entityType: "gdelt" };
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
export function toSelectedEntity(item: any, entityType: string): SelectedEntity {
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

/** Apply active filters to an entity list for a given layer */
function applyFilters(items: any[], layerId: string, filters?: Record<string, string[]>): any[] {
  if (!filters || !Object.values(filters).some(v => v.length > 0)) return items;
  switch (layerId) {
    case "flights": {
      const dep = filters.commercial_departure || [];
      const arr = filters.commercial_arrival || [];
      const air = filters.commercial_airline || [];
      if (!dep.length && !arr.length && !air.length) return items;
      return items.filter(f => {
        if (dep.length && !dep.includes(f.origin_name || "")) return false;
        if (arr.length && !arr.includes(f.dest_name || "")) return false;
        if (air.length && !air.includes(f.airline_code || "")) return false;
        return true;
      });
    }
    case "military": {
      const mc = filters.military_country || [];
      const mt = filters.military_aircraft_type || [];
      if (!mc.length && !mt.length) return items;
      return items.filter(f => {
        if (mc.length && !mc.includes(f.country || "")) return false;
        if (mt.length && !mt.includes(f.military_type || "")) return false;
        return true;
      });
    }
    case "tracked": {
      const tc = filters.tracked_category || [];
      const to = filters.tracked_owner || [];
      if (!tc.length && !to.length) return items;
      return items.filter(f => {
        if (tc.length && !tc.includes(f.alert_category || "")) return false;
        if (to.length && !to.includes(f.alert_operator || "")) return false;
        return true;
      });
    }
    case "private":
    case "jets": {
      const pc = filters.private_callsign || [];
      const pt = filters.private_aircraft_type || [];
      if (!pc.length && !pt.length) return items;
      return items.filter(f => {
        if (pc.length && !pc.includes(f.callsign || "")) return false;
        if (pt.length && !pt.includes(f.aircraft_type || "")) return false;
        return true;
      });
    }
    case "ships_military":
    case "ships_cargo":
    case "ships_civilian":
    case "ships_passenger":
    case "ships_tracked_yachts": {
      const sn = filters.ship_name || [];
      const st = filters.ship_type || [];
      if (!sn.length && !st.length) return items;
      return items.filter(s => {
        if (sn.length && !sn.includes(s.name || "")) return false;
        if (st.length && !st.includes(s.type || "")) return false;
        return true;
      });
    }
    default:
      return items;
  }
}

export function useCategoryCycler(
  data: DashboardData,
  onSelect: (entity: SelectedEntity | null) => void,
  onFlyTo: (lat: number, lng: number) => void,
  activeFilters?: Record<string, string[]>,
) {
  const [activeLayer, setActiveLayer] = useState<string | null>(null);
  const [index, setIndex] = useState(0);

  const entities = useMemo(() => {
    if (!activeLayer) return { items: [], entityType: "" };
    const raw = getEntities(activeLayer, data);
    return { items: applyFilters(raw.items, activeLayer, activeFilters), entityType: raw.entityType };
  }, [activeLayer, data, activeFilters]);

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
      const raw = getEntities(layerId, data);
      const items = applyFilters(raw.items, layerId, activeFilters);
      setActiveLayer(layerId);
      setIndex(0);
      if (items.length > 0) flyToItem(items[0], raw.entityType);
    },
    [activeLayer, data, flyToItem, onSelect, activeFilters],
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
