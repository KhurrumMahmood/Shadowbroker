/**
 * Renders ESRI World Imagery satellite tiles as SVG <image> elements
 * behind D3 map projections. No API key required for visualization use.
 */
import type { GeoProjection } from "d3";

const TILE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

function lat2tile(lat: number, z: number): number {
  return Math.floor(
    ((1 - Math.log(Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)) / Math.PI) / 2) *
      (1 << z),
  );
}

function lng2tile(lng: number, z: number): number {
  return Math.floor(((lng + 180) / 360) * (1 << z));
}

function tile2lat(y: number, z: number): number {
  const n = Math.PI - (2 * Math.PI * y) / (1 << z);
  return (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
}

function tile2lng(x: number, z: number): number {
  return (x / (1 << z)) * 360 - 180;
}

/** Estimate a reasonable zoom level from the projection scale. */
function scaleToZoom(scale: number): number {
  // d3 scale ~150 ≈ zoom 1, ~300 ≈ zoom 2, etc.
  const z = Math.round(Math.log2(scale / 150));
  return Math.max(1, Math.min(z, 8));
}

interface TileOptions {
  /** CSS filter for dark aesthetic. Default: `brightness(0.4) contrast(1.2) saturate(0.6)` */
  filter?: string;
  /** Opacity 0-1. Default 0.5 */
  opacity?: number;
  /** Override automatic zoom level */
  zoom?: number;
}

/**
 * Render ESRI satellite tiles into an SVG group, positioned via the given
 * D3 projection. Call this after creating the SVG but before drawing
 * overlay layers (land outlines, chokepoints, entities, etc.).
 */
export function renderSatelliteTiles(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  group: any, // d3 Selection
  projection: GeoProjection,
  width: number,
  height: number,
  options: TileOptions = {},
): void {
  const {
    filter = "brightness(0.4) contrast(1.2) saturate(0.6)",
    opacity = 0.5,
    zoom: zoomOverride,
  } = options;

  const scale = (projection as { scale?: () => number }).scale?.() ?? 150;
  const zoom = zoomOverride ?? scaleToZoom(scale);

  // Calculate visible geographic bounds from the four corners of the SVG
  const corners = [
    projection.invert?.([0, 0]),
    projection.invert?.([width, 0]),
    projection.invert?.([width, height]),
    projection.invert?.([0, height]),
  ].filter(Boolean) as [number, number][];

  if (corners.length < 2) return;

  const lngs = corners.map((c) => c[0]);
  const lats = corners.map((c) => c[1]);
  const west = Math.max(-180, Math.min(...lngs));
  const east = Math.min(180, Math.max(...lngs));
  const south = Math.max(-85, Math.min(...lats));
  const north = Math.min(85, Math.max(...lats));

  const tyMin = lat2tile(north, zoom); // north = smaller tile y
  const tyMax = lat2tile(south, zoom);
  const txMin = lng2tile(west, zoom);
  const txMax = lng2tile(east, zoom);

  for (let ty = tyMin; ty <= tyMax; ty++) {
    for (let tx = txMin; tx <= txMax; tx++) {
      const tileTopLeft = projection([tile2lng(tx, zoom), tile2lat(ty, zoom)]);
      const tileBotRight = projection([tile2lng(tx + 1, zoom), tile2lat(ty + 1, zoom)]);
      if (!tileTopLeft || !tileBotRight) continue;

      const tileW = tileBotRight[0] - tileTopLeft[0];
      const tileH = tileBotRight[1] - tileTopLeft[1];
      if (tileW <= 0 || tileH <= 0) continue;

      group
        .append("image")
        .attr("href", TILE_URL.replace("{z}", String(zoom)).replace("{y}", String(ty)).replace("{x}", String(tx)))
        .attr("x", tileTopLeft[0])
        .attr("y", tileTopLeft[1])
        .attr("width", tileW)
        .attr("height", tileH)
        .attr("opacity", opacity)
        .style("filter", filter);
    }
  }
}
