/**
 * Build a single searchable string from all meaningful fields on an entity.
 * Used for client-side text filtering within a layer.
 */
export function getSearchableText(entity: Record<string, any>): string {
  const parts: string[] = [];
  // Common identifiers
  for (const key of [
    "callsign", "icao24", "registration", "name", "title",
    "mmsi", "id", "node_id", "slug", "airline", "airline_code",
    "country", "place", "region_name", "company", "tracked_name",
    "yacht_name", "model", "military_type", "alert_category",
    "alert_operator", "location",
  ]) {
    const v = entity[key];
    if (v != null && v !== "") parts.push(String(v));
  }
  // GDELT / nested properties
  if (entity.properties) {
    for (const key of ["action_geo_cc", "action_geo_name", "actor1_name", "actor2_name"]) {
      const v = entity.properties[key];
      if (v != null && v !== "") parts.push(String(v));
    }
  }
  return parts.join(" ");
}

/**
 * Pre-compute a lowercase search index for a list of entities.
 * Call once when the item list changes, then pass to searchWithIndex on each keystroke.
 */
export function buildSearchIndex(items: Record<string, any>[]): string[] {
  return items.map((item) => getSearchableText(item).toLowerCase());
}

/**
 * Filter and rank entities using a pre-computed search index.
 * Returns all items when query is empty.
 * Exact field matches are sorted first, then partial matches.
 */
export function searchWithIndex<T extends Record<string, any>>(
  items: T[],
  index: string[],
  query: string,
): T[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;

  const scored: { item: T; score: number }[] = [];

  for (let i = 0; i < items.length; i++) {
    if (!index[i].includes(q)) continue;

    const item = items[i];
    let score = 1;
    for (const key of ["callsign", "name", "mmsi", "icao24", "title", "id"]) {
      const v = item[key];
      if (v != null && String(v).toLowerCase() === q) {
        score = 2;
        break;
      }
    }
    scored.push({ item, score });
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.map((s) => s.item);
}

/**
 * Filter and rank entities by a text query.
 * Convenience wrapper that builds the index inline — prefer buildSearchIndex + searchWithIndex
 * for repeated searches on the same list.
 */
export function searchEntities<T extends Record<string, any>>(
  items: T[],
  query: string,
): T[] {
  return searchWithIndex(items, buildSearchIndex(items), query);
}
