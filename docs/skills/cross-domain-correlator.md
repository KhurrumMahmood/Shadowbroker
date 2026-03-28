# Skill: Cross-Domain Correlator

Parallel sub-agent pattern for discovering correlations across ShadowBroker's data domains.
This is the core differentiator — no one else does multi-domain movement intelligence.

## When to Use

- User asks a question that spans multiple data domains
- Generating deep briefs or region dossiers
- Running EXP-001 (Commodity Trader) or EXP-012 (Cascade Detection)
- Proactive alert generation (agent detects multi-domain anomaly)
- Investigating a specific event's broader context

## Architecture: Parallel Domain Agents + UNION Merge

```
User Query / Trigger Event
        |
        v
  +-----------+
  | Orchestrator |  -- Parses query, selects relevant domains, builds shared context
  +-----------+
        |
        +---> [Aviation Agent]   -- Queries ADS-B, military flights, plane_alert
        +---> [Maritime Agent]   -- Queries AIS, yacht_alert, vessel_alert, carriers
        +---> [Financial Agent]  -- Queries oil, defense stocks, shipping rates
        +---> [Conflict Agent]   -- Queries ACLED/GDELT, news, frontlines, liveuamap
        +---> [Cyber Agent]      -- Queries Shodan, IODA, KiwiSDR
        +---> [Environmental Agent] -- Queries earthquakes, fires, weather
        |
        v
  +-----------+
  | UNION Merge |  -- Combines findings, detects cross-domain links
  +-----------+
        |
        v
  Correlation Report
```

Each domain agent runs independently, writes findings to a structured format, and returns.
The orchestrator never passes one agent's findings to another during collection — this prevents confirmation bias.

## Shared Context (passed to every domain agent)

```
Query Context:
  Original Query:    [user's question or trigger event description]
  AOR:               [bounding box or region]
  Time Window:       [start, end in UTC]
  Focus Entities:    [specific callsigns, MMSIs, IPs, org names if mentioned]
  Hypothesis:        [if the user has one, state it — agents should test, not confirm]
```

## Domain Agent Template

Each domain agent follows the same structure:

```
DOMAIN AGENT: [Domain Name]
CONTEXT: [Shared context injected here]

TASK:
1. Query all feeds in your domain for the AOR and time window
2. For each relevant record, extract an evidence record (see below)
3. Score each record for anomaly level
4. Identify domain-specific patterns (see domain pattern library below)
5. Produce a domain summary with findings ranked by importance
6. Flag anything that MIGHT correlate with other domains (spatial, temporal, entity overlap)

OUTPUT FORMAT:
Write findings to a structured list. Each finding:
  - Finding ID: [DOMAIN-NNN]
  - Description: [What was observed]
  - Evidence: [Specific data points — callsigns, MMSIs, coordinates, timestamps]
  - Anomaly Level: [Normal | Notable | Anomalous | Critical]
  - Confidence: [High | Medium | Low]
  - Source Tier: [T1-T5]
  - Correlation Hooks: [entities, locations, or time windows that other domains should check]

DO NOT:
  - Speculate about what other domains will find
  - Adjust your findings based on what you think the "answer" should be
  - Omit normal findings — absence of anomaly in your domain is data too
  - Over-classify anomaly levels — "Critical" means imminent, not just interesting
```

## Domain Pattern Libraries

### Aviation Patterns
```
- Unusual military flight density in region (compare to 7-day baseline)
- Surveillance orbits (loitering patterns, racetrack holds)
- Notable aircraft (plane_alert DB matches) in unexpected locations
- Tanker/refueling aircraft indicating sustained operations
- Flight path deviations from normal routes
- Altitude anomalies (military low-level vs normal)
- Transponder on/off transitions (squawk changes)
```

### Maritime Patterns
```
- AIS dark periods (vessel stops transmitting — evasion?)
- Unusual port calls (vessel type doesn't match port type)
- Ship-to-ship transfers at sea (STS — sanctions evasion indicator)
- Tanker loitering near oil infrastructure
- Naval vessel movements outside normal patrol areas
- Flag anomalies (vessel flag doesn't match owner nationality)
- Speed anomalies (stopped in shipping lane, excessive speed in port approach)
- CCG/navy vessel proximity to disputed features
```

### Financial Patterns
```
- Oil price movement diverging from physical supply signals
- Defense stock spikes preceding public news
- Shipping rate changes in specific routes
- Commodity price anomalies in regions with physical activity
- Sanctions-related entity financial activity
```

### Conflict Patterns
```
- GDELT event density spikes (Goldstein scale trending negative)
- News clustering on specific locations
- Frontline changes (LiveUAMap/frontlines data)
- Protest/unrest indicators (ACLED event types)
- Information operations signals (coordinated narrative shifts in GDELT)
- Casualty reports correlating with observed military activity
```

### Cyber Patterns
```
- New ICS/SCADA devices appearing in conflict zones (Shodan)
- Internet outages (IODA) correlating with physical events
- Exposed infrastructure near military installations
- Vulnerability exposure changes (new CVEs on critical infrastructure)
- Radio traffic anomalies (KiwiSDR)
- GPS jamming/spoofing zones
```

### Environmental Patterns
```
- Earthquake → infrastructure outage cascade
- Fire → flight diversion or maritime rerouting
- Space weather → comms disruption
- Weather → operational window (clear weather + military activity = potential operation)
```

### Prediction Market Patterns
```
- Conflict market probability spike (delta > 10pp) + military flight increase = compound signal
- Market volume surge as proxy for attention/uncertainty
- Divergence between market odds and physical sensors (market pessimistic but no ground-truth)
```

### Information Operations Patterns
```
- FIMI major wave + low GDELT = manufactured crisis
- FIMI + high GDELT = amplification of real events
- Coordinated narrative shifts across multiple actors targeting same country
```

### Transport/Logistics Patterns
```
- Train delays + internet outages = infrastructure cascade indicator
- Multi-modal transport disruption (trains + ships + outages in same region)
- Meshtastic node density as connectivity resilience proxy in disrupted areas
```

## UNION Merge Rules

After all domain agents return, the orchestrator merges findings:

### 1. Dedup
Same entity appearing in multiple domains → link, don't duplicate.
Example: A tanker vessel appears in both Maritime (AIS position) and Financial (oil price context) → single entity with dual-domain evidence.

### 2. Spatial Correlation
Findings from different domains within N km of each other → flag as spatially correlated.
```
Default radius thresholds:
  Maritime + Aviation:     50 km  (ship and aircraft near each other)
  Any + Infrastructure:    25 km  (event near a power plant, military base, datacenter)
  Any + Conflict:         100 km  (event in active conflict zone)
  Cyber + Physical:        50 km  (Shodan device near physical event)
  Air Raids + Military:   100 km  (active combat)
  FIMI + Conflict:        Country-level match (narrative targeting)
  Markets + Physical:     Thematic match (same topic/region, not spatial)
```

### 3. Temporal Correlation
Findings from different domains within N time of each other → flag as temporally correlated.
```
Default time thresholds:
  Same-hour:    Strong correlation signal
  Same-day:     Moderate correlation signal
  Same-week:    Weak correlation (note but don't overweight)
```

### 4. Entity Correlation
Same entity (by name, ID, or org) appearing across domains → high-value link.
```
Entity linkage keys:
  Aircraft:   ICAO hex, callsign, tail number, operator
  Vessel:     MMSI, IMO number, vessel name, owner/operator
  Person/Org: Name match (fuzzy), sanctions list ID
  Location:   Coordinates within threshold, facility name match
  IP/Cyber:   IP address, ASN, organization name
```

### 5. Conflict Resolution
When domain agents report contradictory information:
- **Both agents cite T1/T2 sources:** Present both. This is valuable — it may indicate deception, confusion, or a developing situation.
- **One T1/T2, one T3+:** Prefer the higher-tier source but note the contradiction.
- **Both T3+:** Present as unresolved with both sources cited.

**Never silently resolve contradictions.** Contradictions between domains are often the most important signal.

### 6. Absence as Evidence
If a domain agent reports NO anomalies in a region where other domains show significant activity, that's meaningful:
- Military flights increasing but maritime traffic unchanged → air-only operation?
- Conflict events but no internet outage → infrastructure intact or pre-positioned?
- Financial indicators moving but no physical activity → market speculation, not ground truth?

## Correlation Scoring

After merge, each cross-domain link gets a score:

```
Correlation Score = Domain Count * Evidence Strength * Temporal Weight * Novelty

Where:
  Domain Count:      Number of domains with corroborating evidence (2-6)
  Evidence Strength: Average source tier of contributing evidence (T1=5, T2=4, T3=3, T4=2, T5=1)
  Temporal Weight:   Same-hour=3, Same-day=2, Same-week=1
  Novelty:          Is this a known/expected correlation (1) or surprising (2)?

Thresholds:
  Score >= 30:  Critical — surface immediately as alert
  Score >= 15:  Significant — lead item in brief
  Score >= 8:   Notable — include in brief
  Score < 8:    Background — log but don't highlight
```

## Output Format

```
CROSS-DOMAIN CORRELATION REPORT
AOR: [Region] | Period: [Time Window] | Generated: [Timestamp]

CORRELATION SUMMARY
[1-2 sentences: what is the headline cross-domain finding?]

HIGH-CONFIDENCE CORRELATIONS (Score >= 15)
1. [Title] — Score: [N] | Confidence: [High/Medium]
   Domains: [Aviation, Maritime, Financial]
   Evidence:
     - [AVN-001] [Aviation finding]
     - [MAR-003] [Maritime finding]
     - [FIN-002] [Financial finding]
   Assessment: [What this combination suggests]

2. [...]

NOTABLE CORRELATIONS (Score 8-14)
[...]

ABSENCE SIGNALS
- [Domain X showed no anomalies despite activity in Domain Y — significance: ...]

DOMAIN-ONLY FINDINGS (no cross-domain link but individually important)
- [DOMAIN-NNN] [Finding that didn't correlate but is still significant]

CONTRADICTIONS
- [Domain A says X; Domain B says Y — possible explanations: ...]

RAW EVIDENCE TABLE
| ID | Domain | Type | Entity | Coordinates | Time | Anomaly | Confidence | Source Tier |
|----|--------|------|--------|-------------|------|---------|------------|-------------|
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
```

## Failure Modes

| Failure | Symptom | Fix |
|---------|---------|-----|
| **Confirmation bias** | All findings support the hypothesis, no contradictions | Review: did agents suppress counter-evidence? Re-run with explicit "find counter-evidence" instruction |
| **Spurious correlation** | High score driven by spatial proximity alone with no logical link | Add domain-relevance check: does this correlation make operational sense? |
| **Feed staleness** | Correlation uses data from different time periods (fresh ADS-B + stale GDELT) | Check feed freshness timestamps before correlating; flag stale feeds |
| **Single-domain masquerade** | "Correlation" is actually the same event reported by two feeds in the same domain | Dedup within domain before cross-domain merge |
| **Missing domain** | A domain agent fails/times out, merge proceeds without it | Always report which domains contributed and which were missing |
| **Over-alerting** | Too many "critical" correlations desensitize the consumer | Calibrate scoring thresholds monthly; critical should be rare (<1/day) |
