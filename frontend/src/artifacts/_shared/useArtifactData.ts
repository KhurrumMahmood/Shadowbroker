import { useState, useEffect } from "react";

/**
 * Hook for artifact components to receive data.
 *
 * When rendered inside a sandboxed iframe (HTML artifacts), listens for
 * `shadowbroker:data` postMessage events from ArtifactPanel.
 * When rendered inline (React artifacts), uses initialData props only —
 * the postMessage listener is skipped to avoid a same-origin message
 * injection surface.
 *
 * @param initialData - Optional initial data (primary source for inline React artifacts)
 * @returns The latest data payload
 */
export function useArtifactData<T = unknown>(initialData?: T): T | undefined {
  const [data, setData] = useState<T | undefined>(initialData);

  // Only listen for postMessage inside iframes (HTML artifact context).
  // Inline React artifacts receive data via props, not postMessage.
  const isInIframe = typeof window !== "undefined" && window.parent !== window;

  useEffect(() => {
    if (!isInIframe) return;

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
  }, [isInIframe]);

  return data;
}
