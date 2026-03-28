import { useState } from "react";
import { useDataPolling, type BackendStatus } from "./useDataPolling";
import { useSnapshotData } from "./useSnapshotData";

/**
 * Thin router that reads ?demo= and ?overlay= URL params and returns data from
 * either the live polling hook or a static snapshot.
 *
 * Both hooks always execute (React rules of hooks), but useSnapshotData is a
 * no-op when demoKey is null, and useDataPolling will harmlessly fail if the
 * backend isn't running in demo-only scenarios.
 */
export function useDashboardDataSource(): {
  data: any;
  dataVersion: number;
  backendStatus: BackendStatus;
  isDemo: boolean;
  demoKey: string | null;
  overlayName: string | undefined;
} {
  const [{ demoKey, overlayName }] = useState(() => {
    if (typeof window === "undefined") return { demoKey: null as string | null, overlayName: undefined as string | undefined };
    const params = new URLSearchParams(window.location.search);
    return { demoKey: params.get("demo"), overlayName: params.get("overlay") ?? undefined };
  });

  const polling = useDataPolling();
  const snapshot = useSnapshotData(demoKey, overlayName);

  return {
    ...(demoKey ? snapshot : polling),
    isDemo: !!demoKey,
    demoKey,
    overlayName,
  };
}
