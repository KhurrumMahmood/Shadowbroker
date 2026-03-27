# Artifact System

Artifacts are reusable data visualizations that the AI agent can display alongside chat conversations. They come in two types: **React** (admin-created, persistent) and **HTML** (AI-generated, ephemeral).

## Showcase Page

Browse all artifacts at `/artifacts`. The page auto-discovers artifacts from `registry.json` and loads fixture data from each artifact's `fixtures.ts` — no manual wiring needed.

## Directory Structure

Each React artifact lives in `frontend/src/artifacts/{name}/`:

```
src/artifacts/
├── _shared/                    # Shared utilities
│   ├── ArtifactShell.tsx       # Card wrapper component
│   ├── dummyData.ts            # Auto-discovery fixture loader
│   ├── types.ts                # Shared TypeScript types
│   └── useArtifactData.ts      # Data hook (props or postMessage)
├── registry.json               # Source of truth for all artifacts
├── chokepoint-risk-monitor/    # Example artifact
│   ├── ChokepointRiskMonitor.tsx   # React component
│   ├── fixtures.ts                 # Dummy data + DATASETS export
│   └── meta.json                   # Metadata (accepts_data schema)
└── ...
```

## Adding a New React Artifact

### Checklist

1. **Create the directory**: `src/artifacts/{name}/`

2. **Create the component** (`{Name}.tsx`):
   ```tsx
   import { useArtifactData } from "../_shared/useArtifactData";

   interface MyData { /* ... */ }

   export default function MyArtifact({ initialData }: { initialData?: MyData }) {
     const data = useArtifactData<MyData>(initialData);
     if (!data) return <div>No data</div>;
     return /* render */;
   }
   ```

3. **Create `fixtures.ts`** with the standardized format:
   ```ts
   export interface MyData { /* ... */ }

   export const DUMMY_MY_DATA: MyData = { /* realistic sample data */ };

   /** Standardized dataset catalog for the artifacts showcase. */
   export const DATASETS = [
     { key: "default", label: "SHORT DESCRIPTIVE LABEL", data: DUMMY_MY_DATA },
     // Optional: additional dataset variants
     // { key: "scenario-b", label: "ALTERNATIVE SCENARIO", data: VARIANT_DATA },
   ] as const;
   ```

4. **Create `meta.json`**:
   ```json
   {
     "name": "my-artifact",
     "title": "My Artifact",
     "type": "react",
     "tags": ["relevant", "tags"],
     "data_signature": "dashboard",
     "accepts_data": {
       "field_name": "Description of what this field expects"
     },
     "created_by_admin": true
   }
   ```

5. **Add to `registry.json`**:
   ```json
   {
     "name": "my-artifact",
     "title": "My Artifact",
     "description": "What this artifact shows",
     "category": "risk-monitoring",
     "tags": ["relevant", "tags"],
     "data_signature": "dashboard",
     "current_version": 1,
     "type": "react",
     "created_by_admin": true,
     "created_at": "2026-03-27T00:00:00.000000+00:00",
     "updated_at": "2026-03-27T00:00:00.000000+00:00"
   }
   ```

6. **Add to `ArtifactPanel.tsx` REACT_ARTIFACTS map** (one line):
   ```ts
   "my-artifact": () => import("@/artifacts/my-artifact/MyArtifact"),
   ```

### What Happens Automatically

- **Showcase page** (`/artifacts`): The sidebar discovers the artifact from `registry.json` and loads fixtures via `dummyData.ts`'s dynamic import auto-discovery. No changes needed.
- **Dataset selector**: Reads the `DATASETS` export from your `fixtures.ts`. Multiple datasets show up as dropdown options.
- **Fake chat**: Falls back to the default conversation for artifacts without a custom one in `fakeChatData.ts`.

### What Requires Manual Wiring

| File | What to Add | Why |
|------|-------------|-----|
| `registry.json` | New entry with `category` | Source of truth for sidebar + backend |
| `ArtifactPanel.tsx` REACT_ARTIFACTS | One-line lazy import | Required for rendering (main app + showcase) |

The fixture loading (`dummyData.ts`) auto-discovers via dynamic import — no entry needed.

## Categories

Artifacts are grouped by category in the showcase sidebar. Current categories are defined in `registry.json`:

| Key | Label | Description |
|-----|-------|-------------|
| `risk-monitoring` | Risk & Monitoring | Real-time risk dashboards and tickers |
| `threat-analysis` | Threat Analysis | Cross-domain correlation and situation reports |
| `entity-tracking` | Entity Tracking | Vessel, aircraft, and asset watchlists |
| `generated` | AI Generated | Ephemeral HTML artifacts created by the AI agent |

To add a new category, add it to the `categories` object in `registry.json`.

## Fixture Convention

### Standard Format

Every `fixtures.ts` MUST export a `DATASETS` array:

```ts
export const DATASETS = [
  { key: "default", label: "LABEL", data: dataObject },
] as const;
```

- `key`: Unique identifier (first entry should be `"default"`)
- `label`: Short uppercase label shown in the dataset selector dropdown
- `data`: The actual data object matching the artifact's expected shape

### Multiple Datasets

To add variant scenarios for an artifact, add more entries:

```ts
export const DATASETS = [
  { key: "default", label: "ALL 6 CHOKEPOINTS", data: FULL_DATA },
  { key: "pacific", label: "PACIFIC FOCUS", data: PACIFIC_DATA },
  { key: "quiet",   label: "QUIET DAY",     data: MINIMAL_DATA },
] as const;
```

The showcase page's dataset selector dropdown automatically shows all options.

### Backward Compatibility

Existing code (e.g., `AIAssistantPanel.tsx`) calls `getDummyData("name")` which returns the first (default) dataset. This is fully backward-compatible.

## HTML Artifacts

HTML artifacts are AI-generated and stored in the backend registry. They:
- Have their own directory with `meta.json` + `v{n}.html` files
- Are fetched via `/api/artifacts/registry/{name}/v/{version}`
- Receive data via `postMessage` from the `ArtifactPanel` iframe host
- Show "REQUIRES BACKEND" in the showcase when the backend is offline
- Use `generated` as their category in `registry.json`

## Key Files

| File | Purpose |
|------|---------|
| `src/artifacts/registry.json` | Source of truth for all artifacts (categories, metadata) |
| `src/artifacts/_shared/dummyData.ts` | Auto-discovery fixture loader with caching |
| `src/artifacts/_shared/useArtifactData.ts` | Hook for receiving data (props or postMessage) |
| `src/components/ArtifactPanel.tsx` | Renders artifacts (React lazy-load or HTML iframe) |
| `src/components/ArtifactBrowser.tsx` | In-chat artifact browser (fetches from API) |
| `src/components/artifacts-list/` | Showcase page components |
| `src/design/artifact-tokens.css` | CSS custom properties injected into HTML artifacts |
