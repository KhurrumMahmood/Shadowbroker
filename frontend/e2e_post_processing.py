"""Playwright E2E tests for the post-processing pipeline.

Tests:
1. Slow-tier API includes coverage_gaps and correlations keys
2. coverage_gaps / correlations are arrays with correct shape (when populated)
3. machine_assessment field appears on news items (when GDELT data exists)
4. SYS.ANALYSIS badge renders in the News Feed UI for assessed items
5. Derived intelligence section appears in LLM system prompt context

Run: cd frontend && python3 e2e_post_processing.py
Requires: dev servers on :3000/:8000, playwright + chromium installed.
"""
import sys
import json
import traceback
from playwright.sync_api import sync_playwright

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
        ctx.add_init_script("""
            localStorage.setItem('shadowbroker_onboarding_complete', 'true');
            localStorage.setItem('shadowbroker_changelog_v0.9.5', 'true');
        """)
        page = ctx.new_page()

        print("\n=== Loading dashboard ===")
        page.goto("http://localhost:3000", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("h1:has-text('WORLDVIEW')", timeout=15000)
        page.wait_for_timeout(2000)

        # Dismiss modals
        for _ in range(3):
            overlay = page.locator("div.fixed.inset-0.bg-black\\/80")
            if overlay.count() > 0 and overlay.first.is_visible():
                close = page.locator("button:has-text('ACKNOWLEDGED')").or_(
                    page.locator("button:has-text('GOT IT')")).or_(
                    page.locator("button:has-text('CLOSE')")).or_(
                    page.locator("button:has-text('Continue')"))
                if close.count() > 0:
                    close.first.click()
                    page.wait_for_timeout(500)
                else:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
            else:
                break

        # ─── CHECK BACKEND ──────────────────────────────────────────
        health = page.evaluate("fetch('/api/health').then(r => r.json()).catch(e => null)")
        if not health or health.get("status") != "ok":
            print("  Backend not reachable — cannot run post-processing tests")
            browser.close()
            return

        sources = health.get("sources", {})
        has_gdelt = sources.get("gdelt", 0) > 0
        has_news = sources.get("news", 0) > 0
        print(f"  Data: gdelt={sources.get('gdelt',0)}, news={sources.get('news',0)}, "
              f"fires={sources.get('firms_fires',0)}")

        # ─── 1. SLOW-TIER API CONTRACT ──────────────────────────────
        print("\n--- 1. Slow-tier API includes post-processing keys ---")
        slow = page.evaluate("fetch('/api/live-data/slow').then(r => r.json()).catch(e => null)")

        if not slow:
            report("Slow-tier API reachable", False, "fetch returned null")
            browser.close()
            return

        report("Slow-tier API reachable", True)

        report("coverage_gaps key exists in slow-tier response",
               "coverage_gaps" in slow,
               f"keys: {list(slow.keys())[:15]}")

        report("correlations key exists in slow-tier response",
               "correlations" in slow,
               f"keys: {list(slow.keys())[:15]}")

        gaps = slow.get("coverage_gaps", None)
        corrs = slow.get("correlations", None)

        report("coverage_gaps is a list",
               isinstance(gaps, list),
               f"type: {type(gaps).__name__}")

        report("correlations is a list",
               isinstance(corrs, list),
               f"type: {type(corrs).__name__}")

        # ─── 2. COVERAGE GAP SHAPE (when populated) ────────────────
        print("\n--- 2. Coverage gap data shape ---")
        if isinstance(gaps, list) and len(gaps) > 0:
            gap = gaps[0]
            report("Gap has 'lat' field", "lat" in gap, f"keys: {list(gap.keys())}")
            report("Gap has 'lon' field", "lon" in gap, f"keys: {list(gap.keys())}")
            report("Gap has 'gdelt_count' field", "gdelt_count" in gap, f"keys: {list(gap.keys())}")
            report("Gap has 'news_count' field (should be 0)",
                   gap.get("news_count") == 0,
                   f"news_count: {gap.get('news_count')}")
            report("Gap has 'top_event_codes' field",
                   "top_event_codes" in gap,
                   f"keys: {list(gap.keys())}")
            print(f"  Info: {len(gaps)} coverage gap(s) detected — "
                  f"top: {gap.get('gdelt_count')} GDELT events at ({gap.get('lat')}, {gap.get('lon')})")
        elif has_gdelt:
            skip("Coverage gap shape", f"GDELT loaded ({sources.get('gdelt',0)} events) but no gaps found — news may cover all conflict regions")
        else:
            skip("Coverage gap shape", "no GDELT data loaded yet")

        # ─── 3. CORRELATION SHAPE (when populated) ──────────────────
        print("\n--- 3. Correlation data shape ---")
        if isinstance(corrs, list) and len(corrs) > 0:
            corr = corrs[0]
            report("Correlation has 'type' field",
                   "type" in corr,
                   f"keys: {list(corr.keys())}")
            report("Correlation type is a known pattern",
                   corr.get("type") in ("military_near_conflict", "fires_near_conflict", "outage_near_conflict"),
                   f"type: {corr.get('type')}")
            report("Correlation has 'conflict_lat' field",
                   "conflict_lat" in corr,
                   f"keys: {list(corr.keys())}")
            report("Correlation has 'distance_km' field",
                   "distance_km" in corr,
                   f"keys: {list(corr.keys())}")
            report("Correlation has 'gdelt_count' field",
                   "gdelt_count" in corr,
                   f"keys: {list(corr.keys())}")
            # Summarize
            types = {}
            for c in corrs:
                t = c.get("type", "?")
                types[t] = types.get(t, 0) + 1
            print(f"  Info: {len(corrs)} correlation(s) — {types}")
        elif has_gdelt:
            skip("Correlation shape", "GDELT loaded but no cross-domain correlations found")
        else:
            skip("Correlation shape", "no GDELT data loaded yet")

        # ─── 4. MACHINE ASSESSMENTS ON NEWS ITEMS ───────────────────
        print("\n--- 4. Machine assessments on news items ---")
        news = slow.get("news", [])
        assessed = [n for n in news if n.get("machine_assessment")]

        if has_news and has_gdelt:
            # At least some news items should have machine_assessment if GDELT is loaded
            report("Some news items have machine_assessment",
                   len(assessed) > 0,
                   f"0/{len(news)} assessed — pipeline may not have run yet (needs slow-tier cycle)")
            if assessed:
                ma = assessed[0]["machine_assessment"]
                report("machine_assessment has 'gdelt_nearby' field",
                       "gdelt_nearby" in ma,
                       f"keys: {list(ma.keys()) if isinstance(ma, dict) else type(ma).__name__}")
                report("machine_assessment has 'fires_nearby' field",
                       "fires_nearby" in ma,
                       f"keys: {list(ma.keys()) if isinstance(ma, dict) else type(ma).__name__}")
                report("machine_assessment has 'outages_nearby' field",
                       "outages_nearby" in ma,
                       f"keys: {list(ma.keys()) if isinstance(ma, dict) else type(ma).__name__}")
                print(f"  Info: {len(assessed)}/{len(news)} news items assessed — "
                      f"first: gdelt={ma.get('gdelt_nearby')}, fires={ma.get('fires_nearby')}, "
                      f"outages={ma.get('outages_nearby')}")
        elif has_news:
            skip("Machine assessments", "news loaded but no GDELT data — pipeline won't produce assessments")
        else:
            skip("Machine assessments", "no news data loaded yet")

        # ─── 5. SYS.ANALYSIS BADGE IN UI ────────────────────────────
        print("\n--- 5. SYS.ANALYSIS badge in News Feed ---")
        if assessed:
            # Ensure layers are on so news renders
            page.locator("button:has-text('ALL')").first.click()
            page.wait_for_timeout(2000)

            # The badge text ">_ SYS.ANALYSIS:" should appear in the news feed
            sys_analysis = page.locator("text=SYS.ANALYSIS")
            report("SYS.ANALYSIS badge renders for assessed news items",
                   sys_analysis.count() > 0,
                   "no SYS.ANALYSIS text found on page")

            # Verify it shows formatted text like "28 conflict events + 22 fires nearby"
            # not "[object Object]"
            nearby_text = page.locator("text=nearby")
            report("Badge shows formatted text (contains 'nearby')",
                   nearby_text.count() > 0,
                   "no 'nearby' text found — may still show [object Object]")

            object_text = page.locator("text=[object Object]")
            report("Badge does NOT show [object Object]",
                   object_text.count() == 0,
                   f"found {object_text.count()} [object Object] occurrences")
        else:
            skip("SYS.ANALYSIS badge", "no assessed news items to render")

        # ─── 6. DATA SUMMARY INCLUDES COUNTS ────────────────────────
        print("\n--- 6. Post-processing counts in full data ---")
        full = page.evaluate("fetch('/api/live-data').then(r => r.json()).catch(e => null)")
        if full:
            report("Full data has coverage_gaps key",
                   "coverage_gaps" in full,
                   f"keys: {[k for k in full.keys() if 'gap' in k or 'corr' in k]}")
            report("Full data has correlations key",
                   "correlations" in full,
                   f"keys: {[k for k in full.keys() if 'gap' in k or 'corr' in k]}")
        else:
            skip("Full data check", "could not fetch /api/live-data")

        # ─── DONE ───────────────────────────────────────────────────
        browser.close()

    print(f"\n{'='*60}")
    print(f"  Post-processing pipeline E2E: {PASS} passed, {FAIL} failed, {SKIP} skipped")
    print(f"{'='*60}")
    if ERRORS:
        print("\nFailures:")
        for name, detail in ERRORS:
            print(f"  - {name}: {detail}")
    return FAIL == 0


if __name__ == "__main__":
    try:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    except Exception:
        traceback.print_exc()
        sys.exit(2)
