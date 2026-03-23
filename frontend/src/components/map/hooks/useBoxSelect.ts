import { useState, useCallback, useRef, useEffect } from "react";
import type { MapRef } from "react-map-gl/maplibre";

export interface BoxSelectResult {
  bounds: { minX: number; minY: number; maxX: number; maxY: number };
  features: Array<{ type: string; name: string; id: string | number }>;
  counts: Record<string, number>;
}

/** Maps MapLibre layer IDs to friendly entity type names */
const LAYER_TYPE_MAP: Record<string, string> = {
  "commercial-flights-layer": "commercial_flight",
  "private-flights-layer": "private_flight",
  "private-jets-layer": "private_jet",
  "military-flights-layer": "military_flight",
  "tracked-flights-layer": "tracked_flight",
  "uav-layer": "uav",
  "ships-layer": "ship",
  "carriers-layer": "carrier",
  "satellites-layer": "satellite",
  "earthquakes-layer": "earthquake",
  "gdelt-layer": "gdelt_incident",
  "liveuamap-layer": "liveuamap",
  "cctv-layer": "cctv",
  "kiwisdr-layer": "kiwisdr",
  "firms-viirs-layer": "firms_fire",
  "internet-outages-layer": "internet_outage",
  "datacenters-layer": "datacenter",
  "power-plants-layer": "power_plant",
  "military-bases-layer": "military_base",
};

export function useBoxSelect(
  mapRef: MapRef | null,
  enabled: boolean,
  onResult: (result: BoxSelectResult | null) => void,
) {
  const [drawing, setDrawing] = useState(false);
  const [box, setBox] = useState<{ startX: number; startY: number; endX: number; endY: number } | null>(null);
  const startRef = useRef<{ x: number; y: number } | null>(null);

  const handleMouseDown = useCallback(
    (e: MouseEvent) => {
      if (!enabled) return;
      e.preventDefault();
      startRef.current = { x: e.offsetX, y: e.offsetY };
      setDrawing(true);
      setBox({ startX: e.offsetX, startY: e.offsetY, endX: e.offsetX, endY: e.offsetY });
    },
    [enabled],
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!drawing || !startRef.current) return;
      setBox({
        startX: startRef.current.x,
        startY: startRef.current.y,
        endX: e.offsetX,
        endY: e.offsetY,
      });
    },
    [drawing],
  );

  const handleMouseUp = useCallback(
    (e: MouseEvent) => {
      if (!drawing || !startRef.current || !mapRef) {
        setDrawing(false);
        setBox(null);
        return;
      }
      const map = mapRef.getMap();
      const minX = Math.min(startRef.current.x, e.offsetX);
      const minY = Math.min(startRef.current.y, e.offsetY);
      const maxX = Math.max(startRef.current.x, e.offsetX);
      const maxY = Math.max(startRef.current.y, e.offsetY);

      // Ignore tiny drags (likely accidental clicks)
      if (maxX - minX < 10 && maxY - minY < 10) {
        setDrawing(false);
        setBox(null);
        startRef.current = null;
        return;
      }

      const rawFeatures = map.queryRenderedFeatures(
        [[minX, minY], [maxX, maxY]] as [[number, number], [number, number]],
      );

      const seen = new Set<string>();
      const features: BoxSelectResult["features"] = [];
      const counts: Record<string, number> = {};

      for (const f of rawFeatures) {
        const layerId = f.layer?.id;
        const entityType = layerId ? LAYER_TYPE_MAP[layerId] : undefined;
        if (!entityType) continue;
        const id = f.properties?.icao24 || f.properties?.mmsi || f.properties?.id || f.properties?.name || "";
        const key = `${entityType}:${id}`;
        if (seen.has(key)) continue;
        seen.add(key);
        const name = f.properties?.callsign || f.properties?.name || f.properties?.place || f.properties?.title || "";
        features.push({ type: entityType, name, id });
        counts[entityType] = (counts[entityType] || 0) + 1;
      }

      onResult({ bounds: { minX, minY, maxX, maxY }, features, counts });
      setDrawing(false);
      setBox(null);
      startRef.current = null;
    },
    [drawing, mapRef, onResult],
  );

  useEffect(() => {
    const canvas = mapRef?.getMap()?.getCanvas();
    if (!canvas || !enabled) return;

    canvas.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      canvas.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [mapRef, enabled, handleMouseDown, handleMouseMove, handleMouseUp]);

  // Clear when disabled
  useEffect(() => {
    if (!enabled) {
      setDrawing(false);
      setBox(null);
      startRef.current = null;
    }
  }, [enabled]);

  return { drawing, box };
}
