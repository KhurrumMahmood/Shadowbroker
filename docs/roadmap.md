# Roadmap

## MCP Apps Compatibility

### Why
MCP Apps is the first official MCP extension (Jan 2026), co-developed by Anthropic and OpenAI. Adopting it makes our artifacts portable across Claude, ChatGPT, VS Code, Goose, and any future MCP Apps host.

### Current State
Our artifact system is architecturally close to MCP Apps already:
- Render React/HTML in iframes (ArtifactPanel)
- Communicate via postMessage (useArtifactData hook)
- Registry with metadata (registry.json + meta.json)

### Gap Analysis
| What we have | What MCP Apps requires |
|-------------|----------------------|
| Custom postMessage format | JSON-RPC over postMessage (`ui/*` methods) |
| `/api/artifacts/registry` REST API | MCP server with `tools/list` + `tools/call` |
| `meta.json` per artifact | Tool annotations with `_meta.ui.resourceUri` |
| Direct iframe src | `ui://` URI scheme for resource discovery |
| No handshake | `ui/initialize` handshake protocol |

### Implementation Path
1. **Add MCP server endpoint** — wrap our registry API as an MCP server (tools = artifacts)
2. **Adopt `ui://` URI scheme** — artifacts declared as UI resources in tool metadata
3. **Implement JSON-RPC bridge** — replace custom postMessage with MCP Apps JSON-RPC dialect
4. **`ui/initialize` handshake** — standard initialization before data exchange
5. **Security model** — iframe sandboxing, CSP headers, auditable message log

### Spec References
- [MCP Apps Spec](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx)
- [MCP Apps Docs](https://modelcontextprotocol.io/docs/extensions/apps)
- [OpenAI Apps SDK](https://developers.openai.com/apps-sdk/quickstart)

## Multi-Theme Support

### Why
Our HUD theme is great for the standalone app but too niche for embedded contexts (ChatGPT, Claude Desktop, VS Code). Need a clean/neutral theme variant.

### Themes to Consider
- **HUD (current)** — dark, cyan accents, monospace, military styling. For standalone app.
- **Clean/Neutral** — standard dark mode, readable fonts, conventional spacing. For embedded/MCP Apps contexts.
- **Light** — for users/orgs that prefer light mode.

### Implementation
- Already have CSS custom properties (`--text-primary`, `--bg-secondary`, etc.) and a `hud-zone` class for matrix theme
- Theme system could be extended with a context-aware default: detect if running inside an MCP Apps host iframe, use neutral theme; standalone, use HUD

## Billing & Payments

### Stripe Integration
- Subscription tiers (Free / Pro / Enterprise)
- Usage metering for API calls and AI queries
- External checkout flow compatible with ChatGPT Apps SDK requirements

### Auth
- Own auth system for standalone app
- OAuth flow for ChatGPT/Claude users redirecting to our domain
- API keys for programmatic access

## Feed Expansion
See `docs/skills/data-source-evaluator.md` for the structured pipeline.

Priority regions from Sprint 0: South Asia feeds (India, Pakistan military, Indian Ocean maritime).

## Agent System
See `docs/skills/agent-patterns.md` for architecture options.

Phase 1 (current): Tool-Use pattern with orchestrator
Phase 2 (planned): Plan-Execute with learning loop, AWS deployment
