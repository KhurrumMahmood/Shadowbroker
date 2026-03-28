# UX Backlog

Issues observed on the live site. Tracked with completion status.

---

## Completed (2026-03-28)

### SHOW N RESULTS in chat — FIXED
Backend was emitting unmatchable IDs (fires: `id:?`, GDELT: aggregate names). Fixed by:
- Adding coordinate-based IDs to fire and GDELT compact formats in `llm_assistant.py`
- Hardening `findEntityInData()`: case-insensitive matching, numeric coordinate comparison, GeoJSON `geometry.coordinates` fallback
- Filtering unreachable entity types (not in `_SEARCH_CONFIG`) from `result_entities`
- Adding `noneResolved` feedback state to `useAIResultCycler`

**Files changed:** `llm_assistant.py`, `useAIResultCycler.ts`, `AIAssistantPanel.tsx`

### Layer search pane — DONE
New `LayerSearchPane.tsx` component. Click a category in the left panel → search/filter pane scoped to that layer. Click-to-select and fly-to. Uses pre-computed search index (`buildSearchIndex()` in `layerSearch.ts`).

### Viewport-specific counts — DONE
Left panel (`WorldviewLeftPanel.tsx`) shows viewport-filtered counts using `viewportFilter.ts` utilities. Ship counts broken down by category via shared `classifyShipCategory()`.

### Composite clustering — DONE
`useCompositeClusters.ts` merges nearby markers across entity types into composite cluster markers at lower zoom levels. Prevents marker overlap.

### Intel feed improvements — DONE
`IntelFeedPanel.tsx`: per-alert copy button (tracks `copiedId` not boolean), fly-to for geo-located alerts, significance score display.

### Aircraft icon redesign — DONE
`AircraftIcons.ts` / `ShadowIcons.ts`: colored outline icons by category, improved visual hierarchy.

### Map declutter — DONE
`mapConstants.ts`: consolidated zoom thresholds. Viewport bounds equality check in `page.tsx` to prevent drag re-render churn.

---

## Open

### Panel z-index stacking — bring to front on click
Panels have fixed z-index (Brief z-400, IntelFeed z-500, AI z-600). Clicking doesn't raise them. Need dynamic z-index manager.

**Files:** `page.tsx`, all panel components.

### Alert detail drill-down
Alert cards show title + description but no significance breakdown, raw data, or component-level scoring.

**Files:** `IntelFeedPanel.tsx`, possibly backend scoring detail exposure.

### Layer toggle chip discoverability
AI renders clickable layer chips but they're easy to miss. May need visual prominence or animation.

**Files:** `AIAssistantPanel.tsx` (`renderCoreChips()`).

### AIS strategic chokepoint subscriptions
AIS WebSocket narrows to viewport. Strategic areas (Hormuz, Malacca, Suez) show zero ships if not recently viewed. Needs always-subscribed regions. `chokepoints.py` has the bbox definitions.

**Files:** `ais_proxy.js`, `ais_stream.py`, `chokepoints.py`.

### Artifacts registry returning 500
The artifacts button in chat shows "REGISTRY UNAVAILABLE". Needs investigation.

### Voice/Comms not requesting mic permission
Clicking voice input doesn't trigger browser mic permission prompt.
