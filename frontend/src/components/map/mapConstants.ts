// Shared map constants
// Extracted from MaplibreViewer.tsx
import type maplibregl from 'maplibre-gl';

// Empty GeoJSON constant — avoids recreating empty objects on every render
export const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

// Cluster icon sizes: [suffix, pixelSize]
export const CLUSTER_SIZES = [['sm', 32], ['md', 40], ['lg', 48], ['xl', 56]] as const;

// Standard icon-size zoom interpolation (raised floor, visible at all zoom levels)
export const ICON_SIZE: maplibregl.ExpressionSpecification = [
    'interpolate', ['linear'], ['zoom'],
    2, 0.6, 5, 0.75, 8, 0.9, 12, 1.0, 16, 1.15
];

// Shadow layer icon-size: +0.03 additive offset from main for subtle 1-2px border
export const SHADOW_ICON_SIZE: maplibregl.ExpressionSpecification = [
    'interpolate', ['linear'], ['zoom'],
    2, 0.63, 5, 0.78, 8, 0.93, 12, 1.03, 16, 1.18
];

// Ship shadow size (ships visible from zoom 4+)
export const SHADOW_SHIP_ICON_SIZE: maplibregl.ExpressionSpecification = [
    'interpolate', ['linear'], ['zoom'],
    4, 0.73, 8, 0.93, 12, 1.03, 16, 1.18
];

// Country-group render order: bottom → top
export const GROUP_RENDER_ORDER = ['other', 'convenience', 'nonaligned', 'csto', 'nato'];

// All cluster layer IDs (for composite cluster queries in Phase 3)
export const ALL_CLUSTER_LAYER_IDS = [
    'firms-clusters',
    'earthquakes-clusters',
    'cctv-clusters',
    'kiwisdr-clusters',
    'meshtastic-clusters',
    'datacenters-clusters',
    'power-plants-clusters',
    // Dynamic per-group layers are added at runtime
];
