/**
 * Central index of dummy data fixtures for all React artifacts.
 * Import this in mapDataForArtifact when useDummyData flag is set.
 *
 * ONLY for development / explicit user request via the AI assistant.
 * Never used in production data flow.
 */

import { DUMMY_CHOKEPOINT_DATA } from "../chokepoint-risk-monitor/fixtures";
import { DUMMY_CONVERGENCE_DATA } from "../threat-convergence-panel/fixtures";
import { DUMMY_SITREP_DATA } from "../sitrep-region-brief/fixtures";
import { DUMMY_TRACKED_DATA } from "../tracked-entity-dashboard/fixtures";
import { DUMMY_TICKER_DATA } from "../risk-pulse-ticker/fixtures";

const DUMMY_DATA_MAP: Record<string, unknown> = {
  "chokepoint-risk-monitor": DUMMY_CHOKEPOINT_DATA,
  "threat-convergence-panel": DUMMY_CONVERGENCE_DATA,
  "sitrep-region-brief": DUMMY_SITREP_DATA,
  "tracked-entity-dashboard": DUMMY_TRACKED_DATA,
  "risk-pulse-ticker": DUMMY_TICKER_DATA,
};

/**
 * Returns dummy data for the given artifact registry name, or undefined
 * if no fixture exists for that artifact.
 */
export function getDummyData(registryName: string): unknown | undefined {
  return DUMMY_DATA_MAP[registryName];
}
