# Business Model & Monetization

## Distribution Channels

### ChatGPT Apps (via MCP Apps standard)
- **Reach**: 910M+ weekly active ChatGPT users, App Directory for discovery
- **Monetization**: No platform rev share. "External Checkout" is the only GA path — users click out to our domain to pay. We handle pricing, billing, taxes via Stripe.
- **Instant Checkout**: Beta, physical goods only, select Shopify partners. Not available to SaaS developers yet.
- **Digital goods/subscriptions**: Not allowed inside ChatGPT as of March 2026. OpenAI says "exploring."
- **Agentic Commerce Protocol**: Open standard for in-chat checkout, expected later 2026. Details TBA.

### Claude Desktop / Anthropic
- Artifacts render natively via MCP Apps. No monetization layer from Anthropic.

### Standalone (our own frontend)
- Full control over billing, UX, and data. Primary revenue channel.

## Lessons from GPT Store Rev Share

OpenAI promised GPT Store revenue sharing in Q1 2024. What happened:
- Launched late, US-only, opaque engagement-based formula
- Pays ~$0.03/conversation. Most creators earn $0. Ceiling ~$100-500/month.
- Creators can't set prices. OpenAI controls the formula and can change it anytime.
- International creators largely excluded.
- Successful builders use the store as a **lead magnet**, monetize externally.

**Takeaway**: Never depend on a platform's rev share. Own the billing relationship. Use platform distribution for discovery, not revenue.

## Monetization Strategy

### Recommended: Own Billing + Platform Distribution
1. **Stripe subscriptions** on our domain (tiered: Free / Pro / Enterprise)
2. **ChatGPT Apps** listing for discovery — free tier or limited preview, auth redirect to our domain for premium
3. **Claude Desktop** / VS Code MCP integration for power users — same auth model
4. **Enterprise direct sales** for custom deployments (self-hosted, dedicated feeds)

### Pricing Dimensions to Explore
- Number of tracked entities / feeds
- API call volume / refresh rate
- AI assistant query budget
- Historical data access depth
- Custom artifact creation
- Alert configuration limits

## Competitive Landscape (as of March 2026)

| Platform | Artifact/App Model | Monetization for Devs |
|----------|-------------------|----------------------|
| OpenAI ChatGPT | Apps SDK (MCP-based), iframe+postMessage | External checkout only. Rev share promised, not delivered. |
| Anthropic Claude | Artifacts + MCP Apps extension | No monetization layer. |
| Google Gemini | Canvas (side-panel editing), no app standard | No third-party app ecosystem. |

All three have converged on iframe + sandboxed HTML + JSON-RPC postMessage for rendering. Differences are in discovery and auth, not architecture.
