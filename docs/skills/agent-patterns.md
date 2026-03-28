# Skill: Agent System Patterns

Reference patterns for ShadowBroker's agent architecture.
Cherry-picked from ReAct, Plan-Execute, and Reflexion research plus operational failure modes.

## Agent Architecture Selection

| User Query Type | Pattern | Why |
|----------------|---------|-----|
| Simple fact lookup ("How many ships in the Red Sea?") | **Tool-Use** (single tool call) | One feed query, one answer. No reasoning loop needed. |
| Multi-step analysis ("What's unusual about flights near Taipei?") | **ReAct** (Reason-Act loop) | Needs observation → reasoning → follow-up queries. Flexible. |
| Cross-domain investigation ("Brief me on South China Sea") | **Plan-Execute** (upfront plan + parallel dispatch) | Decompose into domain tasks, execute in parallel, synthesize. |
| Anomaly investigation ("Why did oil spike while tankers diverted?") | **Reflexion** (self-critique loop) | Needs hypothesis → test → revise cycle. May need multiple iterations. |
| Proactive alerting (no user query) | **Monitor-Trigger** (threshold + escalation) | Continuous background check, alert when thresholds crossed. |

## Pattern 1: Tool-Use (Simple Queries)

```
User Query
    |
    v
Parse intent → Select tool → Call tool → Format response
```

- No reasoning loop, no iteration
- Sub-second latency target
- Used by: most AI assistant queries on the dashboard
- **Bounded:** 1 tool call, 1 response

Example:
```
Q: "How many military flights are over Ukraine right now?"
→ Tool: query_flights(filter="military", bbox=ukraine_bbox)
→ Response: "There are 7 military flights currently tracked over Ukraine."
```

## Pattern 2: ReAct (Reasoning + Acting)

```
User Query
    |
    v
[Thought] What do I need to find out?
    |
    v
[Action] Call a tool
    |
    v
[Observation] Process the result
    |
    v
[Thought] Do I have enough to answer? Or do I need more?
    |
    +---> Need more → [Action] → [Observation] → [Thought] (loop)
    |
    +---> Enough → [Answer]
```

- **Bounded:** Max 5 iterations (configurable). If not converged by iteration 5, respond with what you have + acknowledge gaps.
- **Time budget:** 30 seconds max. Each iteration should take <5s.
- Used by: analytical queries requiring follow-up

Example:
```
Q: "Are there any unusual flight patterns near the Taiwan Strait?"
→ [Thought] Need military flights in Taiwan Strait area
→ [Action] query_flights(filter="military", bbox=taiwan_strait_bbox)
→ [Observation] 12 flights, 3 are C-130 transports
→ [Thought] C-130 transports are unusual here — let me check if this is normal
→ [Action] query_flights(filter="military", bbox=taiwan_strait_bbox, time="7d_baseline")
→ [Observation] Baseline is 1-2 C-130s per week, currently 3 in 24h
→ [Thought] 3x above baseline is significant. Check if there's a correlated event.
→ [Action] query_news(bbox=taiwan_strait_bbox, time="24h")
→ [Observation] GDELT shows "military exercise" headline from Chinese state media
→ [Answer] "Yes — 3 C-130 transport flights detected in the Taiwan Strait in the last 24h, roughly 3x the weekly baseline. Chinese state media reports a military exercise in the area (GDELT source, Medium confidence)."
```

### ReAct Anti-Patterns

- **Infinite loop:** Agent keeps asking for more data without converging. Fix: hard iteration cap + "answer with what you have" fallback.
- **Tool call hallucination:** Agent invents tool names or parameters. Fix: strict tool schema enforcement, refuse unrecognized tools.
- **Observation blindness:** Agent ignores tool results and reasons from its training data instead. Fix: explicit instruction to reason ONLY from tool results, not prior knowledge.
- **Over-querying:** Agent calls the same tool with slightly different parameters hoping for a better answer. Fix: track previous queries, refuse duplicates.

## Pattern 3: Plan-Execute (Parallel Decomposition)

```
User Query
    |
    v
[Plan] Decompose into independent sub-tasks
    |
    v
[Dispatch] Send sub-tasks to domain agents in parallel
    |
    +---> Aviation Agent
    +---> Maritime Agent
    +---> Financial Agent
    +---> Conflict Agent
    |
    v
[Collect] Wait for all agents (with timeout)
    |
    v
[Synthesize] Merge results using UNION rules
    |
    v
[Deliver] Structured response
```

- Used by: cross-domain queries, region dossiers, deep briefs
- See `cross-domain-correlator.md` for the full merge protocol
- **Bounded:** Fixed agent set, per-agent timeout of 15s, total timeout of 30s

### Plan Quality Checklist
```
[ ] Each sub-task is independent (no sub-task depends on another's output)
[ ] Each sub-task maps to exactly one domain agent
[ ] The synthesis step is explicitly defined (not "figure it out later")
[ ] Timeout and failure handling are specified (what if one agent fails?)
[ ] The plan doesn't duplicate work across sub-tasks
```

## Pattern 4: Reflexion (Self-Critique Loop)

```
User Query / Hypothesis
    |
    v
[Generate] Produce initial analysis using ReAct
    |
    v
[Critique] Review own analysis for:
    - Unsupported claims
    - Missing perspectives
    - Logical gaps
    - Alternative explanations
    |
    v
[Revise] Address critique, gather more data if needed
    |
    v
[Check] Is the analysis robust enough?
    |
    +---> No → [Critique] again (max 2 revisions)
    +---> Yes → [Deliver]
```

- Used by: hypothesis-driven investigations, deep analysis
- **Bounded:** Max 2 revision cycles. After 2, deliver with caveats.
- More expensive (2-3x token cost of ReAct). Use only for:
  - User explicitly asks "why" or "investigate"
  - Anomaly score is Critical
  - Multiple contradictory signals detected

### Reflexion Critique Prompts
```
Self-Critique Checklist:
1. Did I consider alternative explanations for the observed pattern?
2. Am I confusing correlation with causation?
3. Is my conclusion supported by T1/T2 sources, or am I relying on T4/T5?
4. What would a skeptic say about this analysis?
5. What data would DISPROVE my conclusion? Did I look for it?
6. Am I anchored on the first hypothesis, or did I genuinely consider alternatives?
```

## Pattern 5: Monitor-Trigger (Proactive Alerting)

```
[Background Loop — runs every N minutes]
    |
    v
[Scan] Check latest data against alert rules
    |
    v
[Score] Anomaly detection across feeds
    |
    v
[Threshold Check] Score > threshold?
    |
    +---> No → continue loop
    +---> Yes → [Escalate]
              |
              v
          [Generate Alert] using ReAct (1-2 iterations max)
              |
              v
          [Deliver] Push notification / store for next brief
```

- Used by: background alerting, proactive intelligence
- Alert rules defined in `agent/alert_checkers.py` and `agent/alert_engine.py`
- **Bounded:** Alert generation limited to 2 ReAct iterations. If can't explain in 2 iterations, surface as "anomaly detected, investigation needed."

## Failure Mode Table

| Failure Mode | Symptoms | Root Cause | Fix |
|-------------|----------|------------|-----|
| **Context overflow** | Agent truncates evidence, loses early findings | Too many tool results in context | Summarize tool results before storing; use file-based evidence tables for large queries |
| **Tool hallucination** | Agent invents tools like `query_satellite_imagery` that don't exist | Tool name not in schema | Strict tool validation; reject and re-prompt on unknown tool |
| **Infinite ReAct loop** | Agent keeps querying without converging | No stopping condition, or the question is unanswerable with available data | Hard iteration cap (5); "answer with what you have" fallback |
| **Confirmation bias** | All evidence supports the first hypothesis, no counter-evidence sought | Agent optimizes for coherence, not accuracy | Reflexion pattern; explicit "seek counter-evidence" in critique step |
| **Stale data masquerade** | Analysis based on data from hours/days ago presented as "current" | Feed freshness not checked | Always check `_mark_fresh` timestamps; flag stale feeds in output |
| **Spurious correlation** | Events linked by proximity alone with no causal logic | Spatial/temporal overlap without domain relevance check | Add "does this make operational sense?" gate to correlation scoring |
| **Single-agent failure** | One domain agent times out, brief is missing a domain | Network issue, feed down, agent bug | Report which domains contributed; never silently omit a domain |
| **Over-alerting** | Too many Critical alerts, consumer ignores them all | Thresholds too low, or anomaly scoring not calibrated | Monthly threshold calibration; Critical should be <1/day average |
| **Under-alerting** | Real events missed because they don't cross threshold | Thresholds too high, or relevant correlation pattern not defined | Review missed events retrospectively; add new patterns |
| **Cost overrun** | Agent burns through API credits or LLM tokens on one query | Unbounded tool calls, unnecessary Reflexion on simple queries | Pattern selection based on query complexity; budget caps per query |

## Sub-Agent Prompt Template

When dispatching a domain-specific sub-agent:

```
You are the [DOMAIN] analysis agent for ShadowBroker.

CONTEXT:
[Shared context — AOR, time window, focus entities, hypothesis]

YOUR DOMAIN FEEDS:
[List of specific feeds this agent can query with tool names]

TASK:
1. Query your domain feeds for the specified AOR and time window
2. Extract evidence records for all relevant entities
3. Score each record for anomaly level (Normal/Notable/Anomalous/Critical)
4. Identify domain-specific patterns (see pattern library)
5. Flag entities, locations, or time windows that other domains should check

CONSTRAINTS:
- Max [5] tool calls
- Time budget: [15] seconds
- Respond ONLY with evidence from your tools, not training data
- Score honestly — most things are Normal and that's fine

OUTPUT: Structured findings list per the Evidence Record format.
```

## Integration Points

These patterns wire into the existing codebase:

```
Orchestrator:   backend/services/agent/orchestrator.py
Sub-agents:     backend/services/agent/sub_agent.py
Tool registry:  backend/services/agent/registry.py
Domain routing: backend/services/agent/router.py
Alert engine:   backend/services/agent/alert_engine.py
Alert rules:    backend/services/agent/alert_checkers.py
Tool impls:     backend/services/agent/tools/{correlation,anomaly,temporal,spatial}.py
Data store:     backend/services/fetchers/_store.py (latest_data dict)
```

## Cost Budget Guidelines

| Query Type | Pattern | Max Tool Calls | Max LLM Rounds | Target Latency |
|-----------|---------|---------------|----------------|----------------|
| Simple fact | Tool-Use | 1 | 1 | <2s |
| Analytical | ReAct | 5 | 5 | <15s |
| Cross-domain brief | Plan-Execute | 5 per agent, 6 agents | 2 per agent + 1 synthesis | <30s |
| Deep investigation | Reflexion | 10 | 8 (3 generate + 3 critique + 2 revise) | <60s |
| Proactive alert | Monitor-Trigger | 2 | 2 | <10s |
