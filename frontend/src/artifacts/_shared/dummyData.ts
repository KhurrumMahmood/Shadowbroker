/**
 * Central index of dummy data fixtures for all React artifacts.
 * Uses dynamic imports so fixtures are code-split and only loaded when needed.
 *
 * ONLY for development / explicit user request via the AI assistant.
 * Never used in production data flow.
 */

const FIXTURE_LOADERS: Record<string, () => Promise<unknown>> = {
  "chokepoint-risk-monitor": () => import("../chokepoint-risk-monitor/fixtures").then((m) => m.DUMMY_CHOKEPOINT_DATA),
  "threat-convergence-panel": () => import("../threat-convergence-panel/fixtures").then((m) => m.DUMMY_CONVERGENCE_DATA),
  "sitrep-region-brief": () => import("../sitrep-region-brief/fixtures").then((m) => m.DUMMY_SITREP_DATA),
  "tracked-entity-dashboard": () => import("../tracked-entity-dashboard/fixtures").then((m) => m.DUMMY_TRACKED_DATA),
  "risk-pulse-ticker": () => import("../risk-pulse-ticker/fixtures").then((m) => m.DUMMY_TICKER_DATA),
};

// Cache loaded fixtures so subsequent calls are synchronous
const cache: Record<string, unknown> = {};

/**
 * Returns dummy data for the given artifact registry name.
 * Loads fixtures lazily on first request, returns cached data thereafter.
 */
export async function getDummyData(registryName: string): Promise<unknown> {
  if (cache[registryName]) return cache[registryName];
  const loader = FIXTURE_LOADERS[registryName];
  if (!loader) return undefined;
  const data = await loader();
  cache[registryName] = data;
  return data;
}
