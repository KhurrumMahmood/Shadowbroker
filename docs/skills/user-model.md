# Skill: User Model and Adaptive Intelligence

How ShadowBroker learns about its users and adapts its outputs accordingly.
Three layers: explicit (questionnaire), behavioral (observation), derived (inference).

## Onboarding Questionnaire

Five questions, <60 seconds. Gets the system 80% of the way to personalized output immediately.

### The Questions

```
1. What's your role?
   [ ] Defense / Intelligence analyst
   [ ] Commodity / Energy trader
   [ ] Journalist / Investigator
   [ ] Humanitarian / NGO worker
   [ ] Compliance / Sanctions analyst
   [ ] Maritime / Shipping operations
   [ ] Insurance / Risk modeler
   [ ] Researcher / Academic
   [ ] Other: ___________

2. What regions matter most to you? (pick up to 3)
   [ ] South China Sea / Taiwan Strait
   [ ] Middle East / Persian Gulf
   [ ] Black Sea / Eastern Europe
   [ ] South Asia / Indian Ocean
   [ ] Horn of Africa / Red Sea
   [ ] Arctic
   [ ] Global — no specific focus
   [ ] Other: ___________

3. What domains are you most fluent in? (pick all that apply)
   [ ] Military aviation (I know what a C-17 sortie means)
   [ ] Maritime / shipping (I know what Aframax and MMSI mean)
   [ ] Financial markets (I know what options flow and Brent crude mean)
   [ ] Cyber / infrastructure (I know what SCADA and CVE mean)
   [ ] Conflict / geopolitics (I know what ACLED and Goldstein scale mean)
   [ ] None of the above — I'm learning

4. What do you want to do first?
   [ ] See what's happening in a specific region right now
   [ ] Monitor specific entities (vessels, aircraft, organizations)
   [ ] Get a daily intelligence brief
   [ ] Explore cross-domain correlations
   [ ] Track sanctions compliance
   [ ] Just explore — show me what's possible

5. How should we communicate with you?
   [ ] Full technical detail — give me coordinates, callsigns, raw data
   [ ] Balanced — explain the important things, skip the obvious
   [ ] Plain language — I'm here for the insights, not the jargon
```

### What the Questionnaire Produces

```
UserProfile:
  persona:           inferred from Q1 (maps to PMF archetypes)
  priority_regions:  from Q2 (sets default map viewport and collection priority)
  domain_fluency:    from Q3 (dict of domain → expert/intermediate/novice)
  initial_intent:    from Q4 (drives Quick Access recommendations)
  complexity_level:  from Q5 (full/balanced/plain — adjusts all output)
```

### Tip: Bootstrap from Existing Profile

"Paste your LinkedIn headline or a 2-sentence description of what you do, and
we'll pre-fill the questionnaire for you."

The AI parses the text, infers likely answers, and presents the pre-filled form
for the user to confirm or adjust. Reduces onboarding to ~10 seconds.

## Behavioral Signals (Observed Over Time)

The system passively records interaction patterns. No explicit user action required.

### What to Track

```
Queries:
  - Topics queried (entities, regions, domains)
  - Query complexity (simple fact vs. multi-step analysis)
  - Jargon used in queries (vocabulary = expertise indicator)
  - Follow-up patterns ("what does X mean?" = domain novice signal)

Engagement:
  - Which brief sections get expanded/drilled into
  - Which brief sections get skipped
  - Which map layers the user toggles on/off
  - Time spent per artifact or view
  - Which alerts get acted on vs. dismissed

Temporal:
  - Session start times (morning prep? breaking-news reactive? end-of-day review?)
  - Session duration
  - Access frequency (daily user vs. event-driven)
  - Day-of-week patterns

Entities:
  - Repeatedly queried entities = implicit watchlist
  - Repeatedly accessed regions = implicit AOR
  - Repeatedly used domain jargon = expertise confirmation
```

### Behavioral Update Rules

```
After 5 sessions:
  - Adjust domain_fluency based on jargon usage and follow-up patterns
  - Suggest a default viewport based on most-accessed region
  - Identify their top 3 implicit watchlist entities

After 20 sessions:
  - Build a domain depth map (per-domain expertise score)
  - Identify their personal significance threshold (what anomaly score they act on)
  - Predict their session pattern (when they'll next log in)
  - Pre-generate their likely first artifact

Continuous:
  - Track alert action rate → adjust alert threshold to match
  - Track skip rate per domain → de-emphasize low-interest domains in briefs
  - Track drill-down depth per domain → match output detail to their actual interest level
```

## Derived Preferences (System Infers)

These are never shown to the user as settings — they're invisible adaptation.

### Complexity Adaptation

Start with the questionnaire setting. Adjust based on behavior.

```
Signals that user wants MORE complexity:
  - Uses domain jargon in queries
  - Requests raw data or coordinates
  - Skips summary sections, goes straight to evidence tables
  - Asks "can you show me the underlying data?"
  → Shift complexity_level toward "full"

Signals that user wants LESS complexity:
  - Asks "what does X mean?" (even once in a domain = novice signal)
  - Ignores evidence tables, reads only summaries
  - Short sessions, high skim rate
  - Asks "so what does this mean?" (wanting interpretation, not data)
  → Shift complexity_level toward "plain" for that domain

Key rule: Complexity adapts PER DOMAIN, not globally.
  A trader may want full technical detail on financial data
  but plain language on military aviation.
```

### Interest Decay

User interests aren't static. Model decay:

```
interest_score(entity) = base_score * decay_factor^(days_since_last_query)

Where:
  base_score = frequency of past interactions with this entity
  decay_factor = 0.9 per day (10% decay)

If interest_score < threshold:
  - Remove from implicit watchlist
  - De-prioritize in briefs
  - Stop pre-generating artifacts for this entity

If user re-engages:
  - Score jumps back immediately
  - This is a "dormant interest" — might still be worth low-priority monitoring
```

## Quick Access Panel

Pre-built artifact templates biased toward the user's profile and behavior.
Displayed prominently on session start.

### Default Quick Access by Persona

```
Commodity Trader:
  [1] Morning Energy Brief — Persian Gulf tanker activity + oil prices + correlations
  [2] Sanctions Watchlist — flagged vessels + dark period tracker
  [3] Shipping Lane Status — chokepoint activity (Hormuz, Malacca, Suez, Bab-el-Mandeb)
  [4] Congressional Trade Signals — recent defense/energy trades + physical correlations

Military Intel:
  [1] AOR Situation Board — current military flights + naval positions + conflict events
  [2] Force Posture Changes — deviation from baseline in priority regions
  [3] Cyber Exposure — Shodan ICS overlay on critical infrastructure
  [4] Signals Snapshot — radio scanner activity + GPS jamming zones

Journalist:
  [1] Story Leads — narrative divergences + coverage gaps + unusual events
  [2] Entity Tracker — watchlist aircraft/vessels with movement summaries
  [3] Source Map — events plotted with source diversity (how many independent sources?)
  [4] Conflict Timeline — chronological event sequence for current stories

Humanitarian:
  [1] Crisis Dashboard — active disasters + displacement indicators + access routes
  [2] Cascade Monitor — multi-hazard compound events (quake + fire + outage)
  [3] Infrastructure Status — power/comms/transport in affected areas
  [4] Population Movement — AIS refugee vessel tracks + conflict displacement patterns

Compliance:
  [1] Sanctions Alert Feed — OFAC/OpenSanctions matches in real-time
  [2] Dark Vessel Monitor — AIS gap tracker + Benford's Law spoofing flags
  [3] Entity Network — ownership chains for flagged vessels/aircraft
  [4] Jurisdiction Exposure — where flagged entities are operating (regulatory implications)
```

### Behavioral Biasing

After observing the user for 5+ sessions:

```
Quick Access slots adapt:
  - Slot 1: Always their most-accessed artifact type
  - Slot 2: Their second-most, OR a new artifact type from their domain they haven't tried
  - Slot 3: A cross-domain view they might not know exists (discovery slot)
  - Slot 4: Rotates based on current events in their priority regions

"Discovery slot" logic:
  If user always views maritime data but never aviation:
    Suggest: "Flights near your watched vessels" (cross-domain bridge)
  If user always views financial but never conflict:
    Suggest: "Conflict events near your tracked commodity infrastructure"
  The goal is to show them the cross-domain value they're missing.
```

### Pre-generation Strategy

```
For daily users:
  - Pre-generate their Slot 1 artifact 15 minutes before their typical session start
  - Cache it. When they open the app, it loads instantly.
  - Show a "Generated at [time]" timestamp so they know it's fresh.

For event-driven users:
  - Pre-generate artifacts when a significant event occurs in their priority regions
  - Push a notification: "[Region]: [Event summary]. Your brief is ready."

For all users:
  - Never pre-generate more than 4 artifacts (server cost + freshness tradeoff)
  - Stale pre-generated artifacts (>30 min old for fast-changing data) get a
    "Refresh" button rather than auto-serving stale intelligence
```

## Privacy and Transparency

```
Principles:
  - Users can see what the system has learned about them (profile page)
  - Users can correct any inference ("No, I'm not interested in Arctic — remove it")
  - Users can reset behavioral data ("Forget my patterns")
  - Behavioral data is never shared between users
  - Explicit profile answers override behavioral inferences when they conflict
  - No behavioral tracking without consent (opt-in during onboarding)

What NOT to store:
  - Raw query text (store topic tags, not the actual words)
  - Precise session timestamps beyond day/hour (don't track minute-by-minute)
  - Any data that could be used to identify the user to other users
```

## Integration with Agent System

The UserModel is a first-class input to every agent decision:

```
Brief generation:
  → UserProfile.domain_fluency    → per-domain jargon level
  → UserProfile.complexity_level  → progressive disclosure depth
  → UserProfile.priority_regions  → which AORs to include
  → UserProfile.persona           → AIDA framing selection

Artifact generation:
  → UserProfile.initial_intent    → default artifact type
  → BehavioralData.top_artifacts  → most-engaged visualization types
  → BehavioralData.session_time   → pre-generation timing

Alert routing:
  → BehavioralData.action_rate    → personal significance threshold
  → UserProfile.complexity_level  → alert format (coordinates vs. summary)
  → BehavioralData.active_hours   → delivery timing

Quick Access:
  → UserProfile.persona           → default slot templates
  → BehavioralData.access_counts  → biased slot ordering
  → DerivedData.discovery_gaps    → cross-domain discovery slot
```
