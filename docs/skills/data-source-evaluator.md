# Skill: Data Source Evaluator

Structured pipeline for evaluating new data sources before integration into ShadowBroker.
Adapted from the deep-research parallel-draft + UNION-merge pattern.

## When to Use

- Evaluating a new API, feed, or dataset for potential integration
- Comparing competing providers for the same data domain
- Reassessing an existing feed (outage, cost change, better alternative)

## Evaluation Spec (define BEFORE research)

Fill this out first. It becomes the contract for the entire evaluation.

```
Feed Name:
Domain:           [Aviation | Maritime | Satellite | Financial | Conflict | Cyber | News | Environmental | Infrastructure | Other]
Feed Type:        [REST API | WebSocket | RSS | Scrape | Bulk File | MQTT | gRPC]
Evaluation Depth: [Quick (1 pass) | Standard (2 pass) | Deep (3 parallel passes)]
Requester:        [Who asked for this / which experiment needs it]

Questions to Answer:
1. What data does this source provide that we don't already have?
2. Does it overlap with existing feeds? Which ones?
3. What's the integration cost (effort, money, complexity)?
4. What's the intelligence value added to cross-domain correlation?
```

## Source Quality Tiers (OSINT-adapted)

| Tier | Description | Examples | Trust Level |
|------|-------------|----------|-------------|
| **T1** | Government/military primary data with SLAs | FAA ADS-B, IMO AIS, NOAA, Space-Track.org, USGS | Authoritative |
| **T2** | Verified commercial feeds with track records | Shodan, FlightAware, MarineTraffic, ACLED, Refinitiv | High |
| **T3** | Established community/aggregator feeds | ADS-B Exchange, OpenSky, GDELT, KiwiSDR network | Medium-High |
| **T4** | Community-curated, crowd-sourced | Radio scanner communities, volunteer CCTV, LiveUAMap | Medium |
| **T5** | Social media, unverified OSINT, single-source | Twitter/X accounts, Telegram channels, blog scrapes | Low — corroborate before relying |

**Rule:** Never build a feed integration relying solely on T5 sources. T4 sources need a fallback or corroboration strategy.

## Pipeline

### Step 1: Intake and Dedup Check

Before any research, check whether we already cover this data:

```
Existing feed overlap check:
- List all current fetchers in backend/services/fetchers/
- Check backend/services/data_fetcher.py scheduler for similar domains
- Search _store.py latest_data keys for related data
- Check test-silo/exploration/data-sources/index.md for prior research
```

If significant overlap exists, the evaluation shifts from "should we add this?" to "is this better than what we have?"

### Step 2: Technical Assessment

Collect hard facts about the source. No opinions yet.

```
API Assessment:
  Endpoint URL:
  Auth Method:          [API Key | OAuth2 | None | Custom]
  Rate Limits:          [requests/sec, requests/day, results/query]
  Data Freshness:       [Real-time (<1s) | Near-real-time (<60s) | Minutes | Hours | Daily | Weekly]
  Historical Data:      [Yes/No, how far back, cost]
  Geographic Coverage:  [Global | Regional (which?) | Country-specific | Patchy]
  Data Format:          [JSON | XML | CSV | GeoJSON | Protocol Buffers | Custom]
  Pagination:           [Offset | Cursor | None | Stream]
  WebSocket/Streaming:  [Yes/No]
  SDK/Client Library:   [Official | Community | Roll-your-own]
  Uptime/SLA:           [Published? What %?]
  Documentation Quality: [Excellent | Good | Sparse | Nonexistent]

Schema Assessment:
  Key Fields:           [List the important data fields returned]
  Geolocation:          [Lat/lng included? | Needs geocoding? | IP-based? | None]
  Temporal:             [Timestamps included? Format? Timezone?]
  Entity IDs:           [MMSI? ICAO? IP? Custom? How to join with our data?]
  Schema Stability:     [Versioned API? Breaking changes history?]

Cost Assessment:
  Free Tier:            [What's included?]
  Paid Plans:           [Pricing tiers, what unlocks at each]
  Our Projected Usage:  [Estimate based on our polling intervals and data volume]
  Monthly Cost:         [$X at our usage level]
```

### Step 3: Integration Complexity

```
Backend Changes Required:
  New fetcher module:    [Yes — estimated lines of code]
  New data model:        [New fields in _store.py? New key in latest_data?]
  Scheduler tier:        [Fast (60s) | Slow (5min) | Very Slow (15min) | On-demand only]
  Dependencies:          [New Python packages? Playwright? System deps?]
  Auth/secrets:          [New env vars needed]
  Error handling:        [Rate limiting strategy, circuit breaker config]
  Test fixtures needed:  [Sample API responses for tests]

Frontend Changes Required:
  New map layer:         [Yes/No — what geometry type?]
  New GeoJSON builder:   [Yes/No — in geoJSONBuilders.ts]
  New HUD panel:         [Yes/No]
  Icon/styling:          [New markers needed?]

Cross-cutting:
  Bbox filtering:        [Does the API support geographic filtering? Or do we filter client-side?]
  ETag/caching:          [Does the API support conditional requests?]
  Dedup with existing:   [How to handle overlapping entities from multiple feeds?]
```

### Step 4: Intelligence Value Assessment

This is the critical differentiator. Rate 1-5 for each:

```
Correlation Potential:
  [ /5] Adds a new domain dimension (something we can't get from any current feed)
  [ /5] Enriches an existing domain (more detail/coverage on something we already have)
  [ /5] Enables cross-domain correlation (links to other feeds by entity, location, or time)
  [ /5] Temporal analysis value (historical data enables backtesting/trend detection)
  [ /5] Alerting value (real-time changes worth surfacing proactively)

  Total: __/25

  Specific correlation opportunities:
  - [Describe 2-3 concrete cross-domain correlations this enables]
  - [Example: "Shodan ICS exposure near power plants from our static dataset"]
  - [Example: "AIS dark vessel detection correlated with sanctions list"]
```

### Step 5: Risk Assessment

```
Risks:
  API Stability:        [Mature/stable | Beta | Experimental | Scrape (fragile)]
  Legal/ToS:            [Commercial use allowed? Attribution required? Redistribution?]
  Single Point of Failure: [Is this the only source for this data? Backup options?]
  Rate Limit Risk:      [Will we hit limits at scale?]
  Data Quality:         [Known issues? Gaps? Biases?]
  Vendor Lock-in:       [Proprietary format? Migration path?]
```

### Step 6: Verdict

```
Recommendation:        [INTEGRATE | DEFER | REJECT | NEEDS MORE RESEARCH]
Priority:              [P1 (next sprint) | P2 (backlog) | P3 (nice-to-have)]
Effort Estimate:       [S (<1d) | M (1-3d) | L (3-5d) | XL (1-2w)]
Dependencies:          [What else needs to happen first?]
Related Experiments:   [Which EXP-NNN from backlog.md does this serve?]

Justification:         [2-3 sentences on why this recommendation]
```

## Multi-Provider Comparison (when evaluating alternatives)

When comparing 2+ providers for the same data domain, run Steps 2-5 for each, then add:

```
Comparison Matrix:
| Criterion         | Provider A | Provider B | Provider C |
|-------------------|-----------|-----------|-----------|
| Coverage          |           |           |           |
| Freshness         |           |           |           |
| Cost              |           |           |           |
| API Quality       |           |           |           |
| Integration Effort|           |           |           |
| Correlation Value |           |           |           |
| Risk              |           |           |           |
| **Winner**        |           |           |           |

Decision: [Provider X] because [reason].
```

## Deep Evaluation (3 parallel passes)

For high-stakes evaluations (expensive APIs, architectural changes, or pivotal data sources), use 3 parallel sub-agents:

- **Agent A:** Technical deep-dive — API exploration, schema analysis, edge case testing
- **Agent B:** Market/competitive analysis — who else uses this? alternatives? pricing trends?
- **Agent C:** Integration architecture — how exactly would this fit into our pipeline?

Each produces a complete, independent assessment. Merge using UNION rule:
- Keep all unique findings from each pass
- When findings overlap, keep the more detailed version
- When findings contradict, flag both with reasoning
- Never silently drop a finding

## Output

Save evaluation to `docs/evaluations/{feed-name}.md` with the filled-in spec.
If the verdict is INTEGRATE, create a task in the experiment backlog linking to the evaluation.
