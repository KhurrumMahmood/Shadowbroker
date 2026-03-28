# Skill: Intelligence Brief Generator

Structured workflow for generating multi-source intelligence briefs from ShadowBroker's live feeds.
Used by both the AI assistant (runtime) and analysts (development/demo).

## When to Use

- User asks "What's happening in [region]?" or "Brief me on [topic/area]"
- Generating a region dossier (`/api/region-dossier`)
- Producing a viewport briefing (`/api/assistant/brief`)
- Creating demo content for specific personas (commodity trader, mil intel, newsroom)

## Brief Spec (implicit or explicit)

Every brief has a spec, even if the user doesn't state one. Infer it from context.

```
Area of Responsibility (AOR):  [Bounding box, country, region name, or "global"]
Time Window:                   [Last 1h | 6h | 24h | 7d | custom]
Domain Focus:                  [All | Aviation | Maritime | Financial | Conflict | Cyber | Specific]
Audience:                      [General | Mil Intel | Commodity Trader | Journalist | Humanitarian | Compliance]
Depth:                         [Flash (2-3 bullets) | Standard (1 page) | Deep (multi-section)]
```

Audience affects:
- **Mil Intel:** Emphasize force posture, flight patterns, base activity, comms intercepts
- **Commodity Trader:** Emphasize tanker movements, pipeline/refinery exposure, commodity prices, supply disruption signals
- **Journalist:** Emphasize news events, source attribution, human impact, story angles
- **Humanitarian:** Emphasize civilian impact, displacement indicators, infrastructure damage, access routes
- **Compliance:** Emphasize sanctions matches, vessel flag anomalies, entity ownership chains

If a UserProfile exists (see `user-model.md`), read `persona`, `domain_fluency`,
`complexity_level`, and `priority_regions` from it to auto-populate these fields.

## Adaptive Complexity

Briefs adapt their language per domain based on the user's fluency level.
See `user-model.md` for how fluency is determined (questionnaire + behavioral signals).

### Progressive Disclosure (all briefs)

Every data point has 4 layers. Default to the layer matching the user's complexity_level.
Allow drill-down to deeper layers on request.

```
Layer 0 (headline):   "Unusual military activity near Taiwan"
Layer 1 (summary):    "3x above baseline transport flights + 2 naval vessels repositioning"
Layer 2 (analysis):   "Pattern matches pre-exercise posture from Feb 2025. Confidence: Medium."
Layer 3 (raw data):   "C-17A ICAO:AE0412 departed Kadena 0342Z, heading 225, FL350..."

complexity_level mapping:
  "plain"    → default to Layer 1, expand to 2 on request
  "balanced" → default to Layer 2, Layer 1 as intro, Layer 3 on request
  "full"     → default to Layer 3, with Layer 1-2 as section headers
```

### Jargon Bridge

When writing about a domain where the user is a novice (domain_fluency = novice),
auto-insert brief inline explanations for domain-specific terms:

```
Expert sees:
  "Three Aframax tankers diverted from Novorossiysk"

Novice sees:
  "Three Aframax tankers (medium-sized oil tankers, ~750K barrels each) diverted
   from Novorossiysk (Russia's largest Black Sea oil export terminal)"

Rules:
  - Explain a term ONCE per brief, on first occurrence
  - Keep explanations parenthetical and under 10 words
  - Never explain terms the user has used in their own queries (they know it)
  - Domain experts get zero jargon bridges in their expert domain
  - Cross-domain terms always get bridges (a maritime expert reading aviation data
    still needs "C-17A" explained as "USAF heavy transport aircraft")
```

### Per-Domain Complexity Example

Same event, three complexity levels:

```
Event: AIS-dark tanker near Strait of Hormuz

Plain (complexity_level: "plain"):
  "An oil tanker stopped broadcasting its location near the Strait of Hormuz
   (the narrow passage where ~20% of global oil passes). It was dark for 6 hours.
   This sometimes indicates sanctions evasion. Confidence: Medium."

Balanced (complexity_level: "balanced"):
  "Aframax tanker MMSI 636019234 went AIS-dark at 26.5N 56.8E for 6h near Hormuz.
   Previous flag: Marshall Islands. Behavior consistent with STS transfer pattern.
   Confidence: Medium (AIS-only, no satellite corroboration)."

Full (complexity_level: "full"):
  "MMSI 636019234 | Aframax | MHL-flagged | Last AIS: 26.5438N 56.8221E 0342Z
   | Dark period: 0342Z-0947Z (6h05m) | Pre-dark heading: 045 @ 8.2kt
   | Post-dark position: 26.6102N 56.7834E | Drift: 7.4nm NE
   | Pattern: consistent with STS transfer (loiter + drift + resume)
   | Benford check: PASS (natural digit distribution)
   | Confidence: Medium | Corroboration: AIS only, SENTINEL-2 overpass in 4h"
```

## Feed Query Plan

Based on the spec, select which feeds to query. Not all briefs need all feeds.

```
Domain -> Feed Mapping:
  Aviation:     flights, military_flights, plane_alert (notable aircraft)
  Maritime:     ships (AIS), yacht_alert, plan_vessel_alert (CCG vessels), carrier_tracker
  Satellite:    satellites (live positions)
  Financial:    defense_stocks, oil prices
  Conflict:     frontlines, gdelt, news, liveuamap, prediction_markets (leading indicators), ukraine_alerts (real-time raids), fimi (info-ops)
  Environmental: earthquakes, fires, weather, space_weather
  Cyber:        internet_outages (IODA), shodan (on-demand), kiwisdr (radio), meshtastic (mesh network resilience)
  Infrastructure: datacenters, military_bases, power_plants (static reference), trains (rail transport status)
  Surveillance: cctv (traffic cameras)
```

**Minimum viable brief:** At least 3 feeds from 2+ domains. A single-domain brief is a report, not intelligence.

## Collection Phase

Query feeds in parallel. For each feed result in the AOR:

```
Evidence Record:
  Feed:          [source feed name]
  Entity:        [aircraft callsign, vessel MMSI, event ID, IP address, etc.]
  Type:          [flight | vessel | earthquake | news_event | cyber_device | etc.]
  Coordinates:   [lat, lng]
  Timestamp:     [ISO 8601 UTC]
  Key Facts:     [2-3 most important data points from this record]
  Source Tier:    [T1-T5 per data-source-evaluator rubric]
  Anomaly Score:  [Normal | Notable | Anomalous | Critical]
```

### Anomaly Scoring

Flag records as anomalous based on:
- **Spatial:** Entity in unusual location (military aircraft over civilian area, tanker in restricted zone)
- **Temporal:** Activity at unusual time (night flights, weekend port calls)
- **Behavioral:** Deviation from pattern (AIS dark period, unusual route, speed change)
- **Cross-domain:** Events in different domains converging on same location/time
- **Historical:** Significant change from baseline (new ICS device, new military deployment)

## Correlation Phase

After collection, look for cross-domain correlations. These are the highest-value findings.

### Correlation Patterns to Check

```
1. Spatial Clustering:
   - Multiple events from different feeds within N km of each other
   - Events near known critical infrastructure (power plants, military bases, datacenters)

2. Temporal Clustering:
   - Events from different feeds within N minutes/hours of each other in same region
   - Unusual spike in activity across multiple feeds simultaneously

3. Entity Chains:
   - Aircraft linked to notable entities (plane_alert) near conflict zones
   - Vessels linked to sanctioned entities (yacht_alert) changing course
   - IP addresses (Shodan) at same coordinates as infrastructure events

4. Pattern Breaks:
   - Normal shipping lanes suddenly empty (blockade? threat?)
   - Military flights increasing in frequency (escalation?)
   - Internet outages (IODA) coinciding with conflict events
   - Financial indicators diverging from physical activity

5. Cascade Sequences:
   - Event A -> Event B -> Event C within time window
   - Example: earthquake -> infrastructure outage -> flight diversions
   - Example: military buildup -> AIS dark ships -> oil price spike

6. Leading Indicators: market odds spiking + physical activity convergence

7. Information Environment: FIMI targeting + GDELT divergence = manufactured vs real crisis
```

### Confidence Levels

Every assertion in the brief carries a confidence level:

| Level | Criteria | Label |
|-------|----------|-------|
| **High** | Multiple independent T1/T2 sources corroborate | "Confirmed" |
| **Medium** | Single T1/T2 source, or multiple T3 sources agree | "Likely" |
| **Low** | Single T3 source, or T4 sources with partial corroboration | "Possible" |
| **Unverified** | Single T4/T5 source, no corroboration | "Unverified — [source]" |

**Rule:** Never present an unverified claim without labeling it. Never present a low-confidence claim as fact.

## Synthesis Phase

Structure the brief based on depth:

### Flash Brief (2-3 bullets, <100 words)
```
FLASH BRIEF: [AOR] | [Time Window] | [Timestamp]

- [Highest-priority finding with confidence level]
- [Second-priority finding]
- [Third-priority finding, if warranted]

Sources: [N] feeds, [M] events analyzed.
```

### Standard Brief (1 page, ~500 words)
```
INTELLIGENCE BRIEF: [AOR]
Period: [Time Window] | Generated: [Timestamp]
Classification: OPEN SOURCE

SITUATION SUMMARY
[2-3 sentence overview of the current state in the AOR]

KEY DEVELOPMENTS
1. [Finding] — [Confidence: High/Medium/Low]
   Sources: [Feed A, Feed B] | [N corroborating data points]

2. [Finding] — [Confidence: High/Medium/Low]
   Sources: [Feed A] | [Details]

3. [Finding] — [Confidence: High/Medium/Low]
   Sources: [Feed A, Feed C] | [Details]

CROSS-DOMAIN CORRELATIONS
- [Correlation between domains, if any detected]
- [What this combination of signals suggests]

ASSESSMENT
[1-2 sentences: what does this mean? what to watch for?]

GAPS AND LIMITATIONS
- [What we couldn't assess due to feed gaps or data limitations]

---
[N] feeds queried | [M] events analyzed | [K] entities tracked
```

### Deep Brief (multi-section, 1000+ words)
Same as Standard but add:
- **Domain-by-domain breakdown** (Aviation, Maritime, Financial, etc.)
- **Historical context** (how does current activity compare to baseline?)
- **Competing hypotheses** (alternative explanations for observed patterns)
- **Recommendations** (what should the consumer do with this information?)
- **Appendix: Evidence Table** (full list of data points with sources)

## Quality Gate

Before delivering the brief, verify:

```
[ ] Every factual claim cites a specific feed and data point
[ ] Every assertion has a confidence level
[ ] At least 2 domains are represented (it's intelligence, not a feed report)
[ ] Cross-domain correlations are checked (even if none found — say so)
[ ] Gaps are acknowledged (missing feeds, coverage holes, data staleness)
[ ] Anomalies are highlighted, not buried
[ ] Audience-appropriate language and emphasis
[ ] Timestamps are UTC and unambiguous
[ ] No stale data presented as current (check feed freshness timestamps)
```

## Anti-Patterns

- **Single-feed report disguised as intelligence:** Dumping ADS-B data is not a brief. Cross-reference or acknowledge the gap.
- **Correlation without evidence:** "This military flight is probably related to the earthquake" needs supporting data, not vibes.
- **Burying the lead:** The most important finding goes first, not last.
- **False precision:** Don't say "23.7% increase" when you have 3 data points. Say "notable increase."
- **Omitting uncertainty:** If you're not sure, say so. Silence on confidence = false confidence.
