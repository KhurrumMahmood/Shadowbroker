/**
 * Build a flyTo URL that preserves demo/overlay params when in demo mode.
 * Used by artifacts to open the main map at a specific location.
 */
export function buildFlyToUrl(lat: number, lng: number, zoom = 10): string {
  const base = `/?flyTo=${lat},${lng},${zoom}`;
  if (typeof window === "undefined") return base;
  const params = new URLSearchParams(window.location.search);
  const demo = params.get("demo");
  if (!demo) return base;
  const overlay = params.get("overlay");
  return `${base}&demo=${encodeURIComponent(demo)}${overlay ? `&overlay=${encodeURIComponent(overlay)}` : ""}`;
}
