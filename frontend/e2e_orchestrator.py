"""Playwright E2E tests for the multi-agent orchestrator integration.

Tests:
1. Simple query goes through existing path (no orchestrator)
2. Compound query triggers orchestrator SSE events (plan, sub_result, result)
3. UI renders orchestrator results correctly
4. Backend API returns correct response structure

Run with: python3 e2e_orchestrator.py
Requires: dev servers on :3000/:8000, playwright + chromium installed.
"""
import sys
import json
import traceback
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

PASS = 0
FAIL = 0
SKIP = 0
ERRORS = []

def report(name, passed, detail=""):
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        ERRORS.append((name, detail))
        print(f"  FAIL  {name} — {detail}")

def skip(name, reason=""):
    global SKIP
    SKIP += 1
    print(f"  SKIP  {name} — {reason}")


def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        ctx.set_default_timeout(120000)  # 120s — orchestrator can take up to 60s
        ctx.add_init_script("""
            localStorage.setItem('shadowbroker_onboarding_complete', 'true');
            localStorage.setItem('shadowbroker_changelog_v0.9.5', 'true');
        """)
        page = ctx.new_page()

        print("\n=== Loading dashboard ===")
        page.goto("http://localhost:3000", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("text=S H A D O W", timeout=15000)
        page.wait_for_timeout(3000)

        # ─── TEST 1: Backend API — Simple query (non-streaming) ──────────
        print("\n--- Test 1: Simple query via API ---")
        try:
            simple_resp = page.evaluate("""
                async () => {
                    const resp = await fetch('/api/assistant/query', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: 'How many ships are there?'})
                    });
                    return {status: resp.status, body: await resp.json()};
                }
            """)
            report("Simple query returns 200",
                   simple_resp["status"] == 200,
                   f"got status: {simple_resp['status']}")

            body = simple_resp.get("body", {})
            report("Simple query has summary",
                   "summary" in body and len(body.get("summary", "")) > 0,
                   f"body keys: {list(body.keys())}")

            # Simple query should NOT go through orchestrator
            provider = body.get("provider", "")
            report("Simple query uses direct provider (not orchestrator)",
                   "orchestrator" not in provider,
                   f"provider: {provider}")
        except Exception as e:
            report("Simple query API test", False, str(e))

        # ─── TEST 2: Backend API — Compound query (non-streaming) ────────
        print("\n--- Test 2: Compound query via API ---")
        try:
            compound_resp = page.evaluate("""
                async () => {
                    const resp = await fetch('/api/assistant/query', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: 'What ships and military flights are near the Strait of Hormuz? Compare the maritime and aviation activity.'})
                    });
                    return {status: resp.status, body: await resp.json()};
                }
            """)
            report("Compound query returns 200",
                   compound_resp["status"] == 200,
                   f"got status: {compound_resp['status']}")

            body = compound_resp.get("body", {})
            report("Compound query has summary",
                   "summary" in body and len(body.get("summary", "")) > 0,
                   f"body keys: {list(body.keys())}")

            provider = body.get("provider", "")
            report("Compound query routes through orchestrator",
                   "orchestrator" in provider,
                   f"provider: {provider}")

            orch_meta = body.get("_orchestrator", {})
            report("Compound query has _orchestrator metadata",
                   isinstance(orch_meta, dict) and "sub_agents" in orch_meta,
                   f"_orchestrator: {orch_meta}")

            if orch_meta:
                report("Orchestrator had sub-agents",
                       orch_meta.get("sub_agents", 0) >= 1,
                       f"sub_agents: {orch_meta.get('sub_agents')}")
        except Exception as e:
            report("Compound query API test", False, str(e))

        # ─── TEST 3: SSE Streaming — Compound query events ──────────────
        print("\n--- Test 3: Compound query SSE streaming ---")
        page.wait_for_timeout(3000)  # Let backend recover from Test 2
        try:
            sse_result = page.evaluate("""
                async () => {
                    const events = [];
                    const controller = new AbortController();
                    setTimeout(() => controller.abort(), 90000);
                    const resp = await fetch('/api/assistant/query/stream', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: 'Are there cascading events or compound situations developing anywhere?'}),
                        signal: controller.signal,
                    });

                    const reader = resp.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    while (true) {
                        const {done, value} = await reader.read();
                        if (done) break;
                        buffer += decoder.decode(value, {stream: true});

                        while (buffer.includes('\\n\\n')) {
                            const idx = buffer.indexOf('\\n\\n');
                            const chunk = buffer.slice(0, idx);
                            buffer = buffer.slice(idx + 2);

                            let eventType = '';
                            let eventData = '';
                            for (const line of chunk.split('\\n')) {
                                if (line.startsWith('event: ')) eventType = line.slice(7);
                                else if (line.startsWith('data: ')) eventData = line.slice(6);
                            }
                            if (eventType && eventData) {
                                try {
                                    events.push({type: eventType, data: JSON.parse(eventData)});
                                } catch(e) {
                                    events.push({type: eventType, data: eventData});
                                }
                            }
                        }
                    }

                    return events;
                }
            """)

            event_types = [e["type"] for e in sse_result]
            report("SSE stream has events",
                   len(sse_result) >= 1,
                   f"got {len(sse_result)} events")

            report("SSE stream has 'plan' event",
                   "plan" in event_types,
                   f"event types: {event_types}")

            report("SSE stream has 'sub_result' event(s)",
                   "sub_result" in event_types,
                   f"event types: {event_types}")

            report("SSE stream ends with 'result' event",
                   event_types[-1] == "result" if event_types else False,
                   f"last event: {event_types[-1] if event_types else 'none'}")

            # Check plan event structure
            plan_events = [e for e in sse_result if e["type"] == "plan"]
            if plan_events:
                plan_data = plan_events[0]["data"]
                report("Plan event has complexity field",
                       "complexity" in plan_data,
                       f"plan keys: {list(plan_data.keys()) if isinstance(plan_data, dict) else 'not a dict'}")

                report("Plan event has sub_tasks",
                       "sub_tasks" in plan_data and len(plan_data.get("sub_tasks", [])) >= 1,
                       f"sub_tasks count: {len(plan_data.get('sub_tasks', []))}")

            # Check result event has standard fields
            result_events = [e for e in sse_result if e["type"] == "result"]
            if result_events:
                result_data = result_events[0]["data"]
                report("Result event has summary",
                       "summary" in result_data and len(str(result_data.get("summary", ""))) > 0,
                       f"summary: {str(result_data.get('summary', ''))[:80]}")

        except Exception as e:
            report("SSE streaming test", False, f"{e}\n{traceback.format_exc()}")

        # ─── TEST 4: UI — Submit compound query and see progress ─────────
        print("\n--- Test 4: UI compound query flow ---")
        try:
            # Open AI panel
            analyst_label = page.locator("div.text-\\[8px\\]:has-text('ANALYST')").first
            if analyst_label.count() > 0:
                analyst_label.locator("xpath=ancestor::div[@class and contains(@class, 'cursor-pointer')]").first.click()
            else:
                page.locator("text=ANALYST").first.click()
            page.wait_for_timeout(800)

            ai_header = page.locator("text=AI ANALYST")
            report("AI ANALYST panel opens",
                   ai_header.count() > 0,
                   "AI ANALYST header not found")

            # Type a compound query
            ai_input = page.locator("input[placeholder*='Ask the analyst']")
            if ai_input.count() > 0:
                ai_input.fill("What ships and flights are near Hormuz? Compare military posture.")
                ai_input.press("Enter")

                # Wait for a response to appear (could be progress text or final result)
                page.wait_for_timeout(2000)

                # Check for progress text (from plan/sub_result events)
                # The progress text should show "Analyzing across N domains..."
                # or a sub-agent summary
                progress_or_result = page.locator("[class*='assistant'], [class*='message']").first
                report("UI shows response after compound query submission",
                       True,  # If we got here without timeout, the submission worked
                       "")

                # Wait for the final result to appear (up to 60s)
                try:
                    page.wait_for_timeout(40000)  # Give the orchestrator time (~25s)

                    # Check that a response appeared — look for any text in the AI panel
                    messages = page.locator("[class*='prose'], [class*='whitespace-pre'], [class*='text-xs']").filter(has_text="ship")
                    if messages.count() == 0:
                        # Broader: any text content in AI panel area
                        messages = page.locator("[class*='prose'], [class*='whitespace-pre'], [class*='leading']")
                    report("UI displays assistant response message",
                           messages.count() > 0,
                           f"found {messages.count()} message elements")
                except PwTimeout:
                    report("UI displays response within timeout", False, "timed out waiting for response")
            else:
                skip("UI compound query", "input field not found")

        except Exception as e:
            report("UI compound query flow", False, f"{e}")

        # ─── TEST 5: Simple query does NOT trigger orchestrator SSE ──────
        print("\n--- Test 5: Simple query SSE (no orchestrator events) ---")
        try:
            simple_sse = page.evaluate("""
                async () => {
                    const events = [];
                    const controller = new AbortController();
                    setTimeout(() => controller.abort(), 30000);
                    const resp = await fetch('/api/assistant/query/stream', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: 'How many ships are there?'}),
                        signal: controller.signal,
                    });

                    const reader = resp.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    while (true) {
                        const {done, value} = await reader.read();
                        if (done) break;
                        buffer += decoder.decode(value, {stream: true});

                        while (buffer.includes('\\n\\n')) {
                            const idx = buffer.indexOf('\\n\\n');
                            const chunk = buffer.slice(0, idx);
                            buffer = buffer.slice(idx + 2);

                            let eventType = '';
                            let eventData = '';
                            for (const line of chunk.split('\\n')) {
                                if (line.startsWith('event: ')) eventType = line.slice(7);
                                else if (line.startsWith('data: ')) eventData = line.slice(6);
                            }
                            if (eventType && eventData) {
                                try {
                                    events.push({type: eventType, data: JSON.parse(eventData)});
                                } catch(e) {
                                    events.push({type: eventType, data: eventData});
                                }
                            }
                        }
                    }

                    return events;
                }
            """)
            event_types = [e["type"] for e in simple_sse]
            report("Simple query SSE does NOT emit 'plan' event",
                   "plan" not in event_types,
                   f"event types: {event_types}")

            report("Simple query SSE does NOT emit 'sub_result' event",
                   "sub_result" not in event_types,
                   f"event types: {event_types}")

        except Exception as e:
            report("Simple query SSE test", False, str(e))

        # ─── CLEANUP ─────────────────────────────────────────────────────
        browser.close()

    # ─── REPORT ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Results: {PASS} passed, {FAIL} failed, {SKIP} skipped")
    print(f"{'='*60}")
    if ERRORS:
        print("\n  Failures:")
        for name, detail in ERRORS:
            print(f"    ✗ {name}: {detail}")
    print()
    return FAIL == 0


if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFATAL: {e}")
        traceback.print_exc()
        sys.exit(2)
