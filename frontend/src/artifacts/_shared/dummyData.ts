/**
 * Auto-discovery fixture loader for all React artifacts.
 *
 * Convention: every artifact directory can contain a `fixtures.ts` that exports
 * a `DATASETS` array. This module discovers them automatically via dynamic
 * import — no manual wiring needed when adding a new artifact.
 *
 * Each DATASETS entry: { key: string; label: string; data: unknown }
 *
 * ONLY for development / the artifacts showcase / explicit user request.
 * Never used in production data flow.
 */

export interface DatasetEntry {
  readonly key: string;
  readonly label: string;
  readonly data: unknown;
}

// Caches: datasets metadata and individual data payloads
const datasetsCache: Record<string, readonly DatasetEntry[]> = {};
const dataCache: Record<string, unknown> = {};

/**
 * Returns the list of available datasets for an artifact.
 * Auto-discovers by importing `../{name}/fixtures` — artifacts only need
 * to export a `DATASETS` array from their `fixtures.ts`.
 */
export async function getDatasets(registryName: string): Promise<readonly DatasetEntry[]> {
  if (datasetsCache[registryName]) return datasetsCache[registryName];
  try {
    // Webpack/Turbopack resolves this pattern at build time to all
    // matching `../*/fixtures` modules, code-split per artifact.
    const mod = await import(`../${registryName}/fixtures`);
    const datasets: readonly DatasetEntry[] = mod.DATASETS ?? [];
    datasetsCache[registryName] = datasets;
    return datasets;
  } catch {
    // No fixtures.ts for this artifact (e.g. HTML-only artifacts)
    datasetsCache[registryName] = [];
    return [];
  }
}

/**
 * Returns dummy data for a given artifact and optional dataset key.
 * Backward-compatible: omitting datasetKey returns the first (default) dataset.
 */
export async function getDummyData(
  registryName: string,
  datasetKey = "default",
): Promise<unknown> {
  const cacheKey = `${registryName}:${datasetKey}`;
  if (cacheKey in dataCache) return dataCache[cacheKey];

  const datasets = await getDatasets(registryName);
  const ds = datasets.find((d) => d.key === datasetKey) ?? datasets[0];
  if (!ds) return undefined;

  dataCache[cacheKey] = ds.data;
  return ds.data;
}
