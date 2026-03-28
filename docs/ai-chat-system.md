# AI Chat System — Architecture & Known Issues

## Overview

`AIAssistantPanel.tsx` is the AI chat panel. It sends queries to `POST /api/assistant/query/stream` (SSE) and renders structured responses with interactive buttons.

## Button Types

The LLM response (parsed by `parse_llm_response()` in `llm_assistant.py`) can produce 8 types of interactive elements:

| Button | Source field | What it does |
|--------|-------------|--------------|
| **SHOW N RESULTS** | `result_entities` | Cycles through entities on the map via `useAIResultCycler` |
| **Layer toggle chips** | `layer_toggles` | Toggles map layers on/off (constrained to `VALID_LAYERS` allowlist) |
| **VIEW ARTIFACT** | `artifact` | Opens the artifact viewer with HTML content |
| **COPY** | Response text | Copies AI response to clipboard |
| **FLY TO** | `flyTo` | Pans map to coordinates |
| **REPLAY ALL** | Conversation history | Replays entire conversation |
| **COMMS (voice)** | Mic input | Records audio, transcribes via STT, sends as query |

## Entity Resolution Chain (SHOW RESULTS)

```
Backend LLM → result_entities: [{type: "ship", id: "EVERGREEN"}]
    ↓
Frontend useAIResultCycler.setResults()
    ↓
TYPE_ALIASES normalizes type strings (plural → singular, aliases)
    ↓
TYPE_TO_DATA_KEY maps entity type → DashboardData key
    ↓
findEntityInData() searches the live data array:
  1. String match on: icao24, mmsi, id, node_id, slug, name, title, properties.name
  2. All comparisons case-insensitive + trimmed
  3. Coordinate fallback: parses "lat,lng" or "lat-lng" IDs → numeric comparison
  4. GeoJSON fallback: checks item.geometry.coordinates for GDELT features
    ↓
Resolved entities → fly to first, cycle with prev/next arrows
```

### Backend constraints

- Only entity types in `_SEARCH_CONFIG` (in `llm_assistant.py`) can produce valid IDs
- `parse_llm_response()` filters out entities whose type is not in `_SEARCH_CONFIG`
- Fires use coordinate IDs: `"lat,lng"` (e.g., `"26.5,56.3"`)
- GDELT uses coordinate IDs from GeoJSON geometry
- Ships use `mmsi`, flights use `icao24`

### Types NOT in _SEARCH_CONFIG (cannot produce SHOW RESULTS)

`satellites`, `cctv`, `kiwisdr`, `prediction_markets`, `ukraine_alerts`, `fimi`, `trains`, `meshtastic`, `gps_jamming`

## Layer Toggle Allowlist

`VALID_LAYERS` in `AIAssistantPanel.tsx` controls which layers the AI can toggle. Currently excludes: `prediction_markets`, `ukraine_alerts`, `fimi`, `trains`, `meshtastic`, `gibs_imagery`, `highres_satellite`.

## Known Issues (as of 2026-03-28)

1. **VIEW ARTIFACT loses metadata on history replay** — `conversationHistory` persists `title` and `content` but not `metadata`. Clicking a replayed artifact chip opens the viewer without metadata context. (Medium)

2. **REPLAY ALL doesn't reopen artifacts** — Replaying messages doesn't restore the artifact viewer state. (Low)

3. **SHOW RESULTS feedback race condition** — 50ms `setTimeout` checks `noneResolved` after `setResults`. Works in practice due to React 18 synchronous batching, but fragile if React changes batching behavior. (Low)

4. **Artifacts button shows "REGISTRY UNAVAILABLE"** — Registry endpoint returning 500. Needs investigation. (Active bug)

5. **Voice/Comms doesn't request mic permission** — Clicking the voice input never triggers the browser mic permission prompt. (Active bug)
