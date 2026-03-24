import maplibregl from "maplibre-gl";

let activeMarker: maplibregl.Marker | null = null;

export function showPulseAt(map: maplibregl.Map, lng: number, lat: number) {
  removePulse();
  const el = document.createElement("div");
  el.className = "entity-pulse-marker";
  activeMarker = new maplibregl.Marker({ element: el, anchor: "center" })
    .setLngLat([lng, lat])
    .addTo(map);
}

export function removePulse() {
  if (activeMarker) {
    activeMarker.remove();
    activeMarker = null;
  }
}
