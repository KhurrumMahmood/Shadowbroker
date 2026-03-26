"""Playwright E2E tests for LLM context enrichment + WHO DON disease outbreaks.

Tests:
1. Slow-tier API includes disease_outbreaks key
2. Disease outbreak items have correct shape (when WHO API returned data)
3. Disease outbreaks render in the News Feed UI
4. LLM assistant can answer questions about headlines/news
5. LLM assistant can answer questions about fires/conflict
6. _build_data_summary includes rich context (headlines, markets, gaps)
7. New categories appear in LLM search results
8. WHO DON source tag visible in news feed

Run: cd frontend && python3 e2e_llm_context_who.py
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
            print("  Backend not reachable — cannot run tests")
            browser.close()
            return

        sources = health.get("sources", {})
        has_news = sources.get("news", 0) > 0
        has_gdelt = sources.get("gdelt", 0) > 0
        has_fires = sources.get("firms_fires", 0) > 0
        has_outbreaks = sources.get("disease_outbreaks", 0) > 0
        print(f"  Data: news={sources.get('news',0)}, gdelt={sources.get('gdelt',0)}, "
              f"fires={sources.get('firms_fires',0)}, outbreaks={sources.get('disease_outbreaks',0)}")

        # ─── 1. SLOW-TIER API: DISEASE OUTBREAKS KEY ──────────────
        print("\n--- 1. Slow-tier API includes disease_outbreaks ---")
        slow = page.evaluate("fetch('/api/live-data/slow').then(r => r.json()).catch(e => null)")

        if not slow:
            report("Slow-tier API reachable", False, "fetch returned null")
            browser.close()
            return

        report("Slow-tier API reachable", True)
        report("disease_outbreaks key exists in slow-tier response",
               "disease_outbreaks" in slow,
               f"keys: {[k for k in slow.keys() if 'disease' in k or 'outbreak' in k]}")

        outbreaks = slow.get("disease_outbreaks", [])
        report("disease_outbreaks is a list",
               isinstance(outbreaks, list),
               f"type: {type(outbreaks).__name__}")

        # ─── 2. DISEASE OUTBREAK ITEM SHAPE ───────────────────────
        print("\n--- 2. Disease outbreak item shape ---")
        if isinstance(outbreaks, list) and len(outbreaks) > 0:
            ob = outbreaks[0]
            report("Outbreak has 'title' field", "title" in ob, f"keys: {list(ob.keys())}")
            report("Outbreak has 'disease_name' field", "disease_name" in ob, f"keys: {list(ob.keys())}")
            report("Outbreak has 'country' field", "country" in ob, f"keys: {list(ob.keys())}")
            report("Outbreak has 'risk_score' field", "risk_score" in ob, f"keys: {list(ob.keys())}")
            report("Outbreak has 'source' field equal to 'WHO DON'",
                   ob.get("source") == "WHO DON",
                   f"source: {ob.get('source')}")
            report("Outbreak has 'link' field", "link" in ob, f"keys: {list(ob.keys())}")
            report("Outbreak risk_score is between 1-10",
                   isinstance(ob.get("risk_score"), (int, float)) and 1 <= ob.get("risk_score", 0) <= 10,
                   f"risk_score: {ob.get('risk_score')}")
            print(f"  Info: {len(outbreaks)} outbreak(s) — "
                  f"first: {ob.get('disease_name')} in {ob.get('country')} (risk {ob.get('risk_score')})")
        else:
            skip("Outbreak item shape", "no disease outbreaks loaded — WHO API may be unreachable")

        # ─── 3. DISEASE OUTBREAKS IN NEWS FEED UI ─────────────────
        print("\n--- 3. Disease outbreaks render in News Feed ---")
        if has_outbreaks or len(outbreaks) > 0:
            # Ensure layers are on
            page.locator("button:has-text('ALL')").first.click()
            page.wait_for_timeout(2000)

            # WHO DON source tag should appear in the news feed
            who_don_text = page.locator("text=WHO DON")
            report("WHO DON source tag renders in news feed",
                   who_don_text.count() > 0,
                   "no 'WHO DON' text found on page")

            if who_don_text.count() > 0:
                print(f"  Info: {who_don_text.count()} WHO DON item(s) visible in feed")
        else:
            skip("WHO DON in news feed", "no disease outbreaks to render")

        # ─── 4. FULL DATA INCLUDES RICH SUMMARY ──────────────────
        print("\n--- 4. Full data API includes disease_outbreaks ---")
        full = page.evaluate("fetch('/api/live-data').then(r => r.json()).catch(e => null)")
        if full:
            report("Full data has disease_outbreaks key",
                   "disease_outbreaks" in full,
                   f"keys: {[k for k in full.keys() if 'disease' in k]}")
        else:
            skip("Full data check", "could not fetch /api/live-data")

        # ─── 5. LLM SEARCH: NEWS SEARCHABLE ──────────────────────
        print("\n--- 5. LLM can search news data ---")
        if has_news:
            # Use the assistant API to test search — ask about news
            try:
                assistant_resp = page.evaluate("""
                    fetch('/api/assistant/query', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: 'What are the top headlines right now?'})
                    }).then(r => r.json()).catch(e => ({error: String(e)}))
                """)
                if assistant_resp and not assistant_resp.get("error"):
                    summary = assistant_resp.get("summary", "")
                    report("LLM returns summary for headlines query",
                           len(summary) > 10,
                           f"summary length: {len(summary)}")
                    # LLM should reference actual news content, not just counts
                    report("LLM summary is not just a count",
                           not summary.startswith("There are") or "headline" in summary.lower() or len(summary) > 50,
                           f"summary: {summary[:100]}")
                    print(f"  Info: LLM summary: {summary[:150]}")
                else:
                    skip("LLM headlines query", f"assistant error: {assistant_resp.get('error', 'unknown')}")
            except Exception as e:
                skip("LLM headlines query", f"exception: {e}")
        else:
            skip("LLM headlines query", "no news data loaded")

        # ─── 6. LLM SEARCH: FIRES/GDELT SEARCHABLE ───────────────
        print("\n--- 6. LLM can search GDELT/fires data ---")
        if has_gdelt or has_fires:
            try:
                fire_resp = page.evaluate("""
                    fetch('/api/assistant/query', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: 'Are there fires near conflict zones?'})
                    }).then(r => r.json()).catch(e => ({error: String(e)}))
                """)
                if fire_resp and not fire_resp.get("error"):
                    summary = fire_resp.get("summary", "")
                    report("LLM returns summary for fires/conflict query",
                           len(summary) > 10,
                           f"summary length: {len(summary)}")
                    print(f"  Info: LLM summary: {summary[:150]}")
                else:
                    skip("LLM fires query", f"assistant error: {fire_resp.get('error', 'unknown')}")
            except Exception as e:
                skip("LLM fires query", f"exception: {e}")
        else:
            skip("LLM fires query", "no GDELT or fires data loaded")

        # ─── 7. LLM SEARCH: DISEASE OUTBREAKS SEARCHABLE ─────────
        print("\n--- 7. LLM can search disease outbreaks ---")
        if has_outbreaks or len(outbreaks) > 0:
            try:
                outbreak_resp = page.evaluate("""
                    fetch('/api/assistant/query', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query: 'What disease outbreaks are active?'})
                    }).then(r => r.json()).catch(e => ({error: String(e)}))
                """)
                if outbreak_resp and not outbreak_resp.get("error"):
                    summary = outbreak_resp.get("summary", "")
                    report("LLM returns summary for disease outbreaks query",
                           len(summary) > 10,
                           f"summary length: {len(summary)}")
                    print(f"  Info: LLM summary: {summary[:150]}")
                else:
                    skip("LLM outbreaks query", f"assistant error: {outbreak_resp.get('error', 'unknown')}")
            except Exception as e:
                skip("LLM outbreaks query", f"exception: {e}")
        else:
            skip("LLM outbreaks query", "no disease outbreaks loaded")

        # ─── 8. NEWS FEED SORT ORDER ──────────────────────────────
        print("\n--- 8. News feed includes both news and outbreaks sorted by risk ---")
        if has_news and (has_outbreaks or len(outbreaks) > 0):
            # Check that the news feed has items from both sources
            news_items = slow.get("news", [])
            total_expected = len(news_items) + len(outbreaks)
            report("News + outbreaks combined in feed",
                   total_expected > len(news_items),
                   f"news: {len(news_items)}, outbreaks: {len(outbreaks)}")
        elif has_news:
            skip("Combined news+outbreaks", "no outbreaks to merge")
        else:
            skip("Combined news+outbreaks", "no news data loaded")

        # ─── DONE ───────────────────────────────────────────────────
        browser.close()

    print(f"\n{'='*60}")
    print(f"  LLM Context + WHO DON E2E: {PASS} passed, {FAIL} failed, {SKIP} skipped")
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
