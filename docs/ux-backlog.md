# UX Backlog — Post-Visual Foundation

Issues observed on the live site (2026-03-27). To be addressed after the visual foundation overhaul (icon sizing, consistent clustering, composite clusters).

---

## Bug Fixes

### "Show N Results" in chat is broken
The button calls `aiCycler.setResults()` which resolves entity IDs via `findEntityInData()` against live data. The user reports it has never worked. Likely cause: entity ID format mismatch between backend response (`result_entities`) and frontend data lookup. Needs debugging with real AI responses.

**Files:** `useAIResultCycler.ts` (resolution logic), `AIAssistantPanel.tsx` (click handler), backend assistant response format.

---

## Interactivity

### Panel z-index stacking — bring to front on click
Currently fixed: Brief z-400, IntelFeed z-500, AI z-600. Clicking a panel doesn't raise it above others. Need a dynamic z-index manager that assigns highest z to the most recently interacted panel.

**Files:** `page.tsx` (panel state), all panel components (ViewportBriefPanel, IntelFeedPanel, AIAssistantPanel).

### Alert detail drill-down (IntelFeedPanel)
Alert cards (e.g., "Disinfo Divergence") show title + description but no way to see underlying data, the significance breakdown (signal/routine sub-scores), or why the system thinks so. Need expandable detail view per alert showing:
- Significance score breakdown (signal components + routine components)
- Raw data from `alert.data`
- "View on map" for geo-located alerts (already exists for some)
- Link to related entities if applicable

**Files:** `IntelFeedPanel.tsx`, may need backend changes to expose component-level scoring detail.

### Layer toggle chips in chat — discoverability
The AI already renders clickable layer chips ("MILITARY ON" / "CARGO OFF") below responses. User didn't notice them. May need visual prominence improvements — larger chips, animation on first appearance, or a brief tooltip.

**Files:** `AIAssistantPanel.tsx` (chip rendering in `renderCoreChips()`).

---

## Viewport Intelligence

### Viewport-specific counts in left panel + Focus Mode
Left panel shows global counts (`data?.ships?.length`). User wants viewport-specific counts with a toggle between global and viewport. A "Focus Mode" that:
- Filters left panel counts to current map bounds
- Makes the AI context-aware of what's in the viewport (already partially done via viewport brief)
- Persists as a mode toggle, not per-query

**Files:** `WorldviewLeftPanel.tsx` (count display), `page.tsx` (map bounds state), `useDataPolling.ts` (data context).

### Layer search pane from left panel
Clicking a layer should open a search/filter pane scoped to that layer. E.g., click "Ships" → type "Strait of Hormuz" → see a list of ships in that area. Results should:
- List with click-to-select and click-to-fly-to
- Cycle through visually (existing category cycler is sequential only, no search)
- Minimizable to a floating bar for cycling without blocking the map
- Draggable to reposition
- Could use the existing AI backend or a simpler text-match filter

**Files:** New component needed. Builds on `useCategoryCycler.ts` pattern.

---

## Data / Architecture

### Ships missing at Strait of Hormuz — AIS viewport subscription
The AIS WebSocket subscription dynamically narrows to the user's current viewport. If you haven't panned to an area recently, no AIS data arrives. Stale vessels are pruned after 15 minutes. This means strategic chokepoints (Hormuz, Malacca, Suez, Bab el-Mandeb, Taiwan Strait) can show zero ships if you haven't looked there.

Needs a "regions of interest" system that keeps strategic areas subscribed regardless of viewport. Could be:
- A static list of always-subscribed bounding boxes for key chokepoints
- User-configurable watchlist regions
- Multiple overlapping AIS subscriptions (one for viewport, one for strategic areas)

**Files:** `ais_proxy.js` (WebSocket subscription), `ais_stream.py` (bbox management), `main.py` (viewport POST handler).
