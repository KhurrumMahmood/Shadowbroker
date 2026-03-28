import { useEffect, useState, useRef } from "react";
import type { BackendStatus } from "./useDataPolling";

/**
 * Loads a frozen snapshot (and optional overlay) from /snapshots/ for demo mode.
 * Returns the same shape as useDataPolling so callers can swap transparently.
 *
 * When `snapshotKey` is null this is a no-op — returns empty data and 'connecting'.
 */
export function useSnapshotData(
  snapshotKey: string | null,
  overlayName?: string,
): { data: any; dataVersion: number; backendStatus: BackendStatus } {
  const dataRef = useRef<any>({});
  const [dataVersion, setDataVersion] = useState(0);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("connecting");

  useEffect(() => {
    if (!snapshotKey) return;
    // Validate key/overlay to prevent path traversal (backend enforces same on write)
    const safePattern = /^[a-zA-Z0-9_-]+$/;
    if (!safePattern.test(snapshotKey)) {
      console.error("Invalid snapshot key:", snapshotKey);
      setBackendStatus("disconnected");
      return;
    }
    if (overlayName && !safePattern.test(overlayName)) {
      console.error("Invalid overlay name:", overlayName);
      setBackendStatus("disconnected");
      return;
    }

    let cancelled = false;

    async function load() {
      try {
        const baseFetch = fetch(`/snapshots/${snapshotKey}.json`);
        const overlayFetch = overlayName
          ? fetch(`/snapshots/${snapshotKey}.overlay.${overlayName}.json`)
          : null;

        const baseRes = await baseFetch;
        if (!baseRes.ok) {
          console.error(`Snapshot fetch failed: ${baseRes.status}`);
          setBackendStatus("disconnected");
          return;
        }
        let merged = await baseRes.json();

        if (overlayFetch) {
          const overlayRes = await overlayFetch;
          if (overlayRes.ok) {
            const overlay = await overlayRes.json();
            merged = { ...merged, ...overlay };
          }
          // Overlay is optional — missing overlay is not an error
        }

        if (cancelled) return;
        // Shallow merge: overlay replaces entire top-level keys (by design).
        // Overlays must provide complete arrays/objects for keys they touch.
        dataRef.current = merged;
        setDataVersion(1);
        setBackendStatus("connected");
      } catch (e) {
        console.error("Failed loading snapshot", e);
        if (!cancelled) setBackendStatus("disconnected");
      }
    }

    load();
    return () => { cancelled = true; };
  }, [snapshotKey, overlayName]);

  return { data: dataRef.current, dataVersion, backendStatus };
}
