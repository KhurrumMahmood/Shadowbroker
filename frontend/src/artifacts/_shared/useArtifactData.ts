import { useState, useEffect } from "react";

/**
 * Hook for artifact components to receive data via postMessage.
 *
 * Listens for `shadowbroker:data` messages from the parent ArtifactPanel.
 * Used by both HTML artifacts (via inline script) and React artifact components.
 *
 * @param initialData - Optional initial data before postMessage arrives
 * @returns The latest data payload
 */
export function useArtifactData<T = unknown>(initialData?: T): T | undefined {
  const [data, setData] = useState<T | undefined>(initialData);

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (
        event.data &&
        typeof event.data === "object" &&
        event.data.type === "shadowbroker:data"
      ) {
        setData(event.data.payload as T);
      }
    }

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  return data;
}
