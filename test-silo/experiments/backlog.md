# Experiment Backlog

Living tracker for small experiments to validate product-market fit before committing to architecture changes.

## Format

| Field | Description |
|-------|-------------|
| ID | EXP-NNN |
| Hypothesis | What we believe will be true |
| Avatar | Who this serves (archetype # from exploration) |
| Axis | 1-Data / 2-PreProcessing / 3-Temporal / 4-Views |
| Effort | S (<1d), M (1-3d), L (3-5d), XL (1-2w) |
| Depends On | Sprint 0 item or other EXP |
| Validation | How we know it worked |
| Status | BACKLOG / IN-PROGRESS / DONE / KILLED |

---

## Experiments

### EXP-001: Commodity Trader Cross-Domain Correlation
- **Hypothesis:** Commodity traders find cross-domain correlation (mil flights + tankers + GDELT + oil) compelling enough to request a demo
- **Avatar:** #9 Commodity Trader (PMF 35/40)
- **Axis:** 2, 4
- **Effort:** S
- **Depends On:** Sprint 0 post-processing + ENERGY preset
- **Validation:** Show 3 energy desk contacts. Ask: "If this existed as an API with alerts, would you pay $5K/mo?"
- **Status:** BACKLOG

### EXP-002: Coverage Gap Detector for Newsrooms
- **Hypothesis:** Coverage gap detector excites newsroom editors enough to request a trial
- **Avatar:** #14 Newsroom Editor (PMF 31/40)
- **Axis:** 2
- **Effort:** S
- **Depends On:** Sprint 0 post-processing
- **Validation:** Blog post about coverage gaps → share with 5 newsroom editors → track responses
- **Status:** BACKLOG

### EXP-003: ACLED Conflict Data
- **Hypothesis:** Adding ACLED conflict data significantly improves GDELT-only conflict detection
- **Avatar:** #1 Mil Intel, #3 Private Intel
- **Axis:** 1
- **Effort:** M
- **Depends On:** None
- **Validation:** Compare conflict event density and accuracy with/without ACLED
- **Status:** BACKLOG

### EXP-004: Professional Theme Toggle
- **Hypothesis:** Removing military aesthetic doubles interest from commercial users (CSS theme toggle)
- **Avatar:** #7, #9, #14
- **Axis:** 4
- **Effort:** L
- **Depends On:** None
- **Validation:** A/B show both versions to 5 commercial contacts, measure engagement
- **Status:** BACKLOG

### EXP-005: REST API for Traders
- **Hypothesis:** A REST API returning JSON correlation alerts is more valuable to traders than a dashboard
- **Avatar:** #9 Commodity Trader
- **Axis:** 4
- **Effort:** L
- **Depends On:** Sprint 0 post-processing
- **Validation:** Build /api/v1/alerts endpoint, share spec with 3 quant/energy contacts
- **Status:** BACKLOG

### EXP-006: Story Objects from GDELT + News
- **Hypothesis:** Pre-processing GDELT + news into "story objects" makes data dramatically easier for AI to use
- **Avatar:** All
- **Axis:** 2
- **Effort:** L
- **Depends On:** Sprint 0 LLM context fix
- **Validation:** Compare AI answer quality before/after story objects on 10 test queries
- **Status:** BACKLOG

### EXP-007: South Asia Coverage
- **Hypothesis:** South Asia preset + feeds resonates with Pakistan/India analysts
- **Avatar:** #11 Pak ISPR, #12 Indian InsurTech
- **Axis:** 1, 4
- **Effort:** M
- **Depends On:** Sprint 0 South Asia feeds + SOUTH_ASIA preset
- **Validation:** Share with 3 South Asia-focused contacts, measure interest
- **Status:** BACKLOG

### EXP-008: Flight Route Inference
- **Hypothesis:** Flight route inference (enriching ADS-B with origin/destination) makes aviation queries answerable
- **Avatar:** All (original motivation for this exploration)
- **Axis:** 2
- **Effort:** L
- **Depends On:** None
- **Validation:** "What planes are going from London to the US?" returns correct results
- **Status:** BACKLOG

### EXP-009: Humanitarian Branding ("CrisisLens")
- **Hypothesis:** Humanitarian-branded version (light theme, "CrisisLens") attracts NGO pilot interest
- **Avatar:** #4 UN OCHA, #6 Refugee
- **Axis:** 4
- **Effort:** M
- **Depends On:** EXP-004 (theme toggle)
- **Validation:** Share with 2 NGO contacts, measure interest
- **Status:** BACKLOG

### EXP-010: Sanctions Cross-Reference
- **Hypothesis:** OpenSanctions + OFAC cross-reference with yacht/jet tracking is compelling for compliance
- **Avatar:** #10 Sanctions
- **Axis:** 1, 2
- **Effort:** M
- **Depends On:** None
- **Validation:** Demo to 2 compliance contacts
- **Status:** BACKLOG

### EXP-011: Tavily Web Search Augmentation
- **Hypothesis:** Tavily web search augmentation per detected story improves intelligence digest quality
- **Avatar:** #3 Private Intel, #14 Newsroom
- **Axis:** 2
- **Effort:** M
- **Depends On:** Sprint 0 LLM context
- **Validation:** Compare digest quality with/without web search on 5 current stories
- **Status:** BACKLOG

### EXP-012: Compound-Event Cascade Detection
- **Hypothesis:** Compound-event cascade detection (quake + fire + outage) is genuinely novel for cat modelers
- **Avatar:** #20 Cat Modeler (PMF 32/40)
- **Axis:** 2, 3
- **Effort:** L
- **Depends On:** Sprint 0 post-processing
- **Validation:** Share cascade API output with 2 ILS fund managers
- **Status:** BACKLOG

### EXP-013: 7-Day Historical Data
- **Hypothesis:** 7-day historical data enables backtesting traders can't get elsewhere (SQLite snapshots)
- **Avatar:** #9 Commodity Trader
- **Axis:** 3
- **Effort:** XL
- **Depends On:** Sprint 0
- **Validation:** "Can I see what happened last Tuesday?" is answerable
- **Status:** BACKLOG

### EXP-014: Interactive Entity Deep-Dives
- **Hypothesis:** Interactive entity deep-dives (all planes in area, all ships of type X) massively improve core UX
- **Avatar:** All
- **Axis:** 4
- **Effort:** L
- **Depends On:** None
- **Validation:** User testing — can novice user find "all military flights near Tehran" in < 30 seconds?
- **Status:** BACKLOG

### EXP-015: AI-Generated Dynamic Views
- **Hypothesis:** AI-generated dynamic views (on-demand map annotations, corridors, highlighted regions) are the killer feature
- **Avatar:** All
- **Axis:** 4
- **Effort:** XL
- **Depends On:** Sprint 0 LLM context, EXP-006
- **Validation:** Demo 3 dynamically-generated views to 5 contacts, measure "wow" reactions
- **Status:** BACKLOG

### EXP-016: Onboarding Questionnaire → Adaptive Briefs
- **Hypothesis:** A 5-question onboarding questionnaire produces persona-adapted briefs that users engage with 2x more than generic briefs
- **Avatar:** All
- **Axis:** 4
- **Effort:** M
- **Depends On:** None
- **Validation:** A/B test with 5 users — generic brief vs. questionnaire-adapted brief. Measure drill-down rate and session duration. Ask: "Did this feel like it was built for you?"
- **Status:** BACKLOG

### EXP-017: Behavioral Learning → Pre-generated Artifacts
- **Hypothesis:** Pre-generating a user's likely first-view artifact based on their access patterns reduces time-to-insight by >50%
- **Avatar:** All (especially #9 Commodity Trader for morning market prep)
- **Axis:** 4
- **Effort:** L
- **Depends On:** EXP-016 (user profile), EXP-015 (dynamic views)
- **Validation:** Measure time from session start to first meaningful interaction before/after. Target: <5 seconds to useful intelligence.
- **Status:** BACKLOG

### EXP-018: Narrative Divergence Detector
- **Hypothesis:** Flagging stories where state media framing diverges >2 sigma from independent media surfaces manipulation that analysts find valuable
- **Avatar:** #1 Mil Intel, #3 Private Intel, #14 Newsroom Editor
- **Axis:** 2
- **Effort:** M
- **Depends On:** EXP-006 (story objects)
- **Validation:** Show 10 flagged divergences to 3 analyst contacts. Ask: "Would you pay for this signal?"
- **Status:** BACKLOG

### EXP-019: Jargon Bridge (Adaptive Complexity)
- **Hypothesis:** Auto-explaining domain jargon in briefs increases engagement from cross-domain users without annoying domain experts
- **Avatar:** All (especially cross-domain users: traders looking at military data, journalists looking at maritime data)
- **Axis:** 4
- **Effort:** S
- **Depends On:** EXP-016 (user profile for domain fluency)
- **Validation:** Track "what does X mean?" follow-up queries before/after. Target: 50% reduction. Also verify experts don't complain.
- **Status:** BACKLOG

### EXP-020: Quick Access Preset Artifacts
- **Hypothesis:** Pre-built artifact templates for top use cases (morning energy brief, regional threat dashboard, sanctions watchlist, cascade monitor) accessed via Quick Access panel dramatically reduce time-to-value for new users
- **Avatar:** All
- **Axis:** 4
- **Effort:** L
- **Depends On:** EXP-015 (dynamic views), EXP-016 (user profile)
- **Validation:** New user onboards → reaches their first "wow" artifact in <30 seconds via Quick Access. Track: do they come back the next day?
- **Status:** BACKLOG

### EXP-021: Congressional Stock Trade Correlation
- **Hypothesis:** Cross-correlating congressional stock trades with physical movement data (mil flights near bases of defense contractors, tanker activity near energy infrastructure) produces signals commodity traders find uniquely valuable
- **Avatar:** #9 Commodity Trader (PMF 35/40)
- **Axis:** 1, 2
- **Effort:** M
- **Depends On:** EXP-001 (commodity trader correlation baseline)
- **Validation:** Show 5 historical congressional trade + physical movement correlations to 3 energy desk contacts. Ask: "Have you seen this signal anywhere else?"
- **Status:** BACKLOG

### EXP-022: Shodan ICS Map Overlay
- **Hypothesis:** A live Shodan ICS/SCADA exposure layer overlaid on power plants and military bases produces a cyber-physical intelligence view no other platform offers
- **Avatar:** #1 Mil Intel, #3 Private Intel, #20 Cat Modeler
- **Axis:** 1, 4
- **Effort:** M
- **Depends On:** SHODAN_API_KEY (paid plan, $69+/mo)
- **Validation:** Demo the cyber-physical overlay for 3 regions (Ukraine, Taiwan, Persian Gulf) to 3 contacts. Ask: "Does seeing exposed ICS devices near physical infrastructure change your threat assessment?"
- **Status:** BACKLOG

### EXP-023: Benford's Law AIS Spoofing Detection
- **Hypothesis:** Applying Benford's Law to AIS position report digit distributions detects spoofed vessel positions that current methods miss
- **Avatar:** #1 Mil Intel, #10 Sanctions, #3 Private Intel
- **Axis:** 2
- **Effort:** M
- **Depends On:** None (can use existing AIS data)
- **Validation:** Run Benford analysis on known-spoofed AIS tracks (documented cases from 2024-2025 Iran/Russia sanctions evasion). Measure: does the statistical test flag them? False positive rate on known-clean tracks?
- **Status:** BACKLOG

### EXP-024: Entity Significance Scoring
- **Hypothesis:** Replacing boolean alert thresholds with a 100-point significance score (Inherent 50 + Contextual 50, from marketing lead scoring) reduces alert fatigue while surfacing higher-value signals
- **Avatar:** All (especially #9 Commodity Trader, #1 Mil Intel)
- **Axis:** 2
- **Effort:** L
- **Depends On:** Cross-layer intelligence expansion (alert checkers + correlation detectors)
- **Validation:** Compare: current boolean alerts produce X alerts/day with Y% dismiss rate. Scored alerts with threshold at 40+ should produce fewer alerts with <30% dismiss rate. Track action rate per score band.
- **Status:** DONE (2026-03-27) — Implemented as unified dual-model scoring with EXP-027. Signal (0-50) + Routine (0-50) → Significance (0-100). 17 profiles covering all 12 checkers + 5 correlation detectors. Frontend badge display in IntelFeedPanel.

### EXP-025: Persona-Adapted AIDA Framing
- **Hypothesis:** Same event described differently per persona (Commodity Trader sees financial impact, Military Intel sees force posture, Journalist sees story angle) increases engagement 2x over generic descriptions
- **Avatar:** All
- **Axis:** 4
- **Effort:** M
- **Depends On:** EXP-016 (user profile/onboarding questionnaire)
- **Validation:** Generate 5 alerts with persona-adapted descriptions. Show each user the generic version and their persona version. Ask: "Which would you act on?" Target: >80% prefer persona version.
- **Status:** BACKLOG

### EXP-026: Alert Routing by Persona
- **Hypothesis:** Suppressing irrelevant alerts per user role (e.g., don't show DISINFO DIVERGENCE to commodity traders, don't show SUPPLY CASCADE to journalists) reduces noise and increases action rate
- **Avatar:** All
- **Axis:** 4
- **Effort:** S
- **Depends On:** EXP-016 (user profile), cross-layer intelligence expansion
- **Validation:** Track: alert dismiss rate before/after routing. Target: <20% dismiss rate (vs current ~40%). Verify no user reports missing an alert they cared about.
- **Status:** BACKLOG

### EXP-027: BaselineStore Adaptive Thresholds
- **Hypothesis:** Using rolling baselines (SnapshotStore/BaselineStore already built in services/agent/stores.py) to replace static thresholds in alert checkers reduces false positives during routine-but-elevated activity (e.g., NATO exercises, election cycles)
- **Avatar:** All (especially #1 Mil Intel, #9 Commodity Trader)
- **Axis:** 2
- **Effort:** L
- **Depends On:** Cross-layer intelligence expansion, existing BaselineStore infrastructure
- **Validation:** Compare alert fire rates during a known NATO exercise: static thresholds fire N times, adaptive thresholds fire M times (M < N/2). Also verify: adaptive thresholds still fire for genuinely anomalous activity during the same period.
- **Status:** DONE (2026-03-27) — Implemented as unified dual-model scoring with EXP-024. BaselineStore z-scores feed routine components when n>=3 observations exist. Graceful degradation: static calibration priors from EXP-031 provide day-1 scoring; adaptive baselines activate automatically as data accumulates.

### EXP-028: Options Chain Anomaly Signals
- **Hypothesis:** Unusual options activity (heavy puts on tanker stocks, abnormal OTM volume on defense tickers) is a leading indicator that commodity traders find uniquely valuable when cross-referenced with physical OSINT
- **Avatar:** #9 Commodity Trader (PMF 35/40)
- **Axis:** 1, 2
- **Effort:** M
- **Depends On:** EXP-021 (congressional trade correlation baseline)
- **Validation:** Backtest: find 5 historical cases where options anomalies preceded physical events (tanker diversions, military deployments). Show to 3 energy desk contacts. Ask: "Would this signal change your trading decisions?"
- **Status:** BACKLOG

### EXP-029: Facility Attribution Engine
- **Hypothesis:** Cross-referencing Shodan device geolocations with our existing infrastructure layers (power plants, military bases, datacenters) produces attributed cyber-physical facility profiles that no other OSINT platform offers
- **Avatar:** #1 Mil Intel, #9 Commodity Trader, #20 Cat Modeler
- **Axis:** 1, 2
- **Effort:** M
- **Depends On:** Shodan API access (Corporate plan, $1,099/mo — not yet available). Can prototype with free /shodan/host/count facets against known facility IP ranges.
- **Validation:** Attribute 50 facilities across 3 regions (Persian Gulf, Taiwan Strait, Eastern Europe). Show attributed profiles to 3 contacts. Ask: "Does knowing the cyber posture of a physical facility change your risk assessment?"
- **Status:** BACKLOG
- **Note:** Shodan access not yet secured. See `docs/shodan-research.md` for full integration roadmap.

### EXP-030: Peer Baselining / Strategic Deviation Detection
- **Hypothesis:** Comparing Shodan infrastructure profiles across companies in a sector reveals outliers that commodity traders and analysts find uniquely valuable as a proxy for otherwise-hidden operational state
- **Avatar:** #9 Commodity Trader, #3 Private Intel
- **Axis:** 1, 2
- **Effort:** L
- **Depends On:** EXP-029 (facility attribution), Shodan Corporate plan for query volume to build sector baselines
- **Validation:** Build Shodan profiles for 10 companies in one energy subsector. Identify the 2-3 outliers. Show to 3 energy desk contacts. Ask: "Does this deviation from sector baseline tell you something you didn't know?"
- **Status:** BACKLOG
- **Note:** Shodan access not yet secured. Requires Corporate plan ($1,099/mo) for adequate query volume.

### EXP-031: System Calibration — Baseline Expectations vs Reality
- **Hypothesis:** Defining explicit "normal" and "abnormal" expectations for each alert checker, correlation detector, and post-processing function — across different global regions — reveals whether deviations are system bugs or incorrect expectations, and systematically improves both
- **Avatar:** All (internal quality / reliability)
- **Axis:** 2 (pre-processing calibration)
- **Effort:** L
- **Depends On:** Cross-layer intelligence expansion (alert checkers, correlation detectors, post-processing)
- **Validation:**
  1. For each alert checker and correlation detector, define per-region baselines: what is the expected fire rate in peacetime (Black Sea, Persian Gulf, Taiwan Strait, US domestic, Europe)?
  2. Generate synthetic/virtual data snapshots representing "normal" conditions per region. Run the full pipeline. Record: which alerts fire, how many, at what severity.
  3. Generate "abnormal" snapshots (escalation scenarios, infrastructure failures, disinformation campaigns). Run again. Record outputs.
  4. Compare outputs against expectations. Categorize deviations:
     - **System bug:** alert fires when it shouldn't (fix the code)
     - **Wrong expectation:** our "normal" definition was wrong (fix the baseline)
     - **Threshold miscalibration:** fires too often or too rarely (tune the threshold)
     - **Missing detection:** doesn't fire when it should (add new logic)
  5. Success = every checker/detector has documented regional baselines, and we can explain every alert it produces.
- **Status:** DONE (2026-03-27) — 68 calibration tests across 6 regions × 12 scenarios, covering all 12 checkers, 5 detectors, 3 post-processing functions, plus integration and staleness edge cases. 817 total backend tests pass.
- **Deviations found:** 3 wrong expectations (airlift_surge threshold, prediction_market geo distance, conflict_escalation source types), 1 test bug (tz-aware vs naive datetime in staleness mock), 2 threshold findings (rf_anomaly GPS ratio format, GDELT category field missing for detector grid binning). Documented in expectation notes.
- **Note:** This is the foundation for EXP-027 (BaselineStore adaptive thresholds). The baselines defined here become the initial values for the adaptive system. Also feeds into EXP-024 (Entity Significance Scoring) — calibrated baselines improve scoring accuracy.

### EXP-032: Significance-Driven Severity (derive_severity wiring)
- **Hypothesis:** Replacing hardcoded alert severity with score-driven severity (>=70 CRITICAL, >=40 ELEVATED, <40 NORMAL) produces more accurate severity labels that better reflect actual threat level
- **Avatar:** All
- **Axis:** 2
- **Effort:** S
- **Depends On:** EXP-024 (significance scoring — DONE)
- **Validation:** Compare: current hardcoded severity vs derived severity across 50+ alerts. Target: derived severity matches analyst judgment >80% of the time. Feature flag allows A/B comparison.
- **Status:** BACKLOG
- **Note:** `derive_severity()` function already exists and is tested in `significance.py`. Needs: feature flag, wiring into `score_alert()`, and opt-in toggle.

### EXP-033: Calibration Significance Assertions
- **Hypothesis:** Adding min/max significance score expectations to the existing 68 calibration tests catches scoring regressions and validates that normal scenarios score 20-45, escalation scenarios score 60-95
- **Avatar:** Internal quality
- **Axis:** 2
- **Effort:** S
- **Depends On:** EXP-024 (DONE), EXP-031 (DONE)
- **Validation:** Extend `CheckerExpectation` and `DetectorExpectation` with `min_significance`/`max_significance` fields. All 68 calibration tests should pass with score range assertions. Best done once real alert data confirms expected score distributions.
- **Status:** BACKLOG

### EXP-034: IntelFeed Significance Sort & Quadrant Display
- **Hypothesis:** Sorting alerts by significance (instead of creation time) and showing signal/routine sub-scores helps analysts quickly distinguish genuine alerts from noise and contested/novel events
- **Avatar:** All (especially #1 Mil Intel, #9 Commodity Trader)
- **Axis:** 4
- **Effort:** S
- **Depends On:** EXP-024 (DONE)
- **Validation:** Show analysts the same feed sorted by time vs significance. Ask: "Which ordering helps you find actionable items faster?" Target: >70% prefer significance sort. Quadrant labels (genuine/noise/contested/novel) should be intuitive without explanation.
- **Status:** BACKLOG
- **Note:** `signal_score` and `routine_score` are already serialized in the alerts API. Frontend needs sort toggle and sub-score tooltip/display.
