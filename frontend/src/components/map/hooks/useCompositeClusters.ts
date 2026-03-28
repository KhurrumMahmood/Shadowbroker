"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { MapRef } from "react-map-gl/maplibre";

export interface CompositeRow {
    type: string;   // display label (e.g. "Ships", "Fires")
    count: number;
    color: string;
}

export interface CompositeCluster {
    lng: number;
    lat: number;
    rows: CompositeRow[];
}

// Entity type metadata: layer-id prefix → display name + color
const LAYER_META: Record<string, { label: string; color: string }> = {
    'firms':          { label: 'Fires',   color: '#ff6600' },
    'earthquakes':    { label: 'Quakes',  color: '#ffaa00' },
    'cctv':           { label: 'CCTV',    color: '#22c55e' },
    'kiwisdr':        { label: 'SDR',     color: '#f59e0b' },
    'meshtastic':     { label: 'Mesh',    color: '#14b8a6' },
    'datacenters':    { label: 'DC',      color: '#a78bfa' },
    'power-plants':   { label: 'Power',   color: '#f59e0b' },
    'ships':          { label: 'Ships',   color: '#67e8f9' },
    'mil':            { label: 'Military', color: '#facc15' },
};

function layerIdToType(layerId: string): string {
    // Handle dynamic per-group layers: "ships-nato-clusters" → "ships", "mil-csto-clusters" → "mil"
    for (const prefix of Object.keys(LAYER_META)) {
        if (layerId.startsWith(prefix)) return prefix;
    }
    return layerId;
}

const MERGE_RADIUS_PX = 75; // screen-space merge radius
const COMPOSITE_ZOOM_THRESHOLD = 7;
const DEBOUNCE_MS = 150;

/**
 * Queries rendered cluster features across all sources at low zoom,
 * groups by screen-space proximity, and merges multi-type groups
 * into composite cluster descriptors.
 */
export function useCompositeClusters(
    mapRef: React.RefObject<MapRef | null>,
    allClusterLayerIds: string[],
    zoom: number,
): CompositeCluster[] {
    const [composites, setComposites] = useState<CompositeCluster[]>([]);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const update = useCallback(() => {
        const map = mapRef.current?.getMap();
        if (!map || zoom >= COMPOSITE_ZOOM_THRESHOLD) {
            setComposites([]);
            return;
        }

        // 1. Gather all visible cluster features across all layers
        const items: { x: number; y: number; lng: number; lat: number; type: string; count: number }[] = [];
        const existingLayers = allClusterLayerIds.filter(id => map.getLayer(id));
        if (existingLayers.length === 0) { setComposites([]); return; }

        const features = map.queryRenderedFeatures(undefined, { layers: existingLayers });
        for (const f of features) {
            if (!f.properties?.cluster) continue;
            const coords = (f.geometry as any).coordinates as [number, number];
            const pt = map.project(coords);
            items.push({
                x: pt.x, y: pt.y,
                lng: coords[0], lat: coords[1],
                type: layerIdToType(f.layer.id),
                count: f.properties.point_count || 1,
            });
        }

        if (items.length === 0) { setComposites([]); return; }

        // 2. Group by screen-space proximity (union-find)
        const parent = items.map((_, i) => i);
        function find(i: number): number { return parent[i] === i ? i : (parent[i] = find(parent[i])); }
        function union(a: number, b: number) { parent[find(a)] = find(b); }

        for (let i = 0; i < items.length; i++) {
            for (let j = i + 1; j < items.length; j++) {
                const dx = items[i].x - items[j].x;
                const dy = items[i].y - items[j].y;
                if (dx * dx + dy * dy < MERGE_RADIUS_PX * MERGE_RADIUS_PX) {
                    union(i, j);
                }
            }
        }

        // 3. Build groups
        const groups = new Map<number, typeof items>();
        for (let i = 0; i < items.length; i++) {
            const root = find(i);
            if (!groups.has(root)) groups.set(root, []);
            groups.get(root)!.push(items[i]);
        }

        // 4. Only emit composites for groups with 2+ distinct entity types
        const result: CompositeCluster[] = [];
        for (const members of groups.values()) {
            const byType = new Map<string, number>();
            let sumLng = 0, sumLat = 0;
            for (const m of members) {
                byType.set(m.type, (byType.get(m.type) || 0) + m.count);
                sumLng += m.lng;
                sumLat += m.lat;
            }
            if (byType.size < 2) continue;

            const rows: CompositeRow[] = [];
            for (const [type, count] of byType) {
                const meta = LAYER_META[type];
                if (meta) rows.push({ type: meta.label, count, color: meta.color });
            }
            rows.sort((a, b) => b.count - a.count); // largest first

            result.push({
                lng: sumLng / members.length,
                lat: sumLat / members.length,
                rows,
            });
        }

        setComposites(result);
    }, [mapRef, allClusterLayerIds, zoom]);

    useEffect(() => {
        const map = mapRef.current?.getMap();
        if (!map || zoom >= COMPOSITE_ZOOM_THRESHOLD) return;

        const debouncedUpdate = () => {
            if (timerRef.current) clearTimeout(timerRef.current);
            timerRef.current = setTimeout(update, DEBOUNCE_MS);
        };

        map.on('moveend', debouncedUpdate);
        map.on('sourcedata', debouncedUpdate);
        // Initial run
        const initTimer = setTimeout(update, 300);

        return () => {
            map.off('moveend', debouncedUpdate);
            map.off('sourcedata', debouncedUpdate);
            clearTimeout(initTimer);
            if (timerRef.current) clearTimeout(timerRef.current);
        };
    }, [update, zoom]);

    return composites;
}
