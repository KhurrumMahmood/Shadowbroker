"""Playwright E2E tests for Artifact Evolution (Steps 4-6).

Tests:
 1-4. Registry search API (matches, no match, missing param, empty)
 5.   Versions API 404 for nonexistent artifact
 6-7. Registry list + versions for existing artifact
 8.   Assistant query accepts active_artifact field
 9.   AI panel opens via ANALYST toggle
10.   Artifacts browser button exists (Layers icon)
11.   Artifacts browser mode opens and shows content
12-14. Regression: health, artifact 404, no JS errors

Run with: python3 e2e_artifact_evolution.py
Requires: dev servers on :3000/:8000
"""
import sys
import json
import traceback
import urllib.request
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

PASS = 0
FAIL = 0
SKIP = 0
ERRORS = []

BASE = "http://localhost:8000"


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


def api_get(path):
    """Direct HTTP GET to backend (avoids Playwright request context timeout issues)."""
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode()
        return resp.status, json.loads(body) if body else None


def api_post(path, body_dict):
    """Direct HTTP POST to backend."""
    data = json.dumps(body_dict).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data,
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def run_tests():
    # ── API Tests (direct HTTP, no Playwright) ──────────────────

    print("\n── Registry Search API ──")

    # 1. Search with tags
    try:
        status, data = api_get("/api/artifacts/registry/search?tags=maritime,map")
        report("Search API returns 200", status == 200, f"status={status}")
        report("Search API returns array", isinstance(data, list), f"type={type(data).__name__}")
    except Exception as e:
        report("Search API", False, str(e))

    # 2. Search with no matching tags
    try:
        status, data = api_get("/api/artifacts/registry/search?tags=zzz_nonexistent_zzz")
        report("Search returns empty for no match",
               status == 200 and isinstance(data, list) and len(data) == 0,
               f"status={status}, len={len(data) if isinstance(data, list) else 'N/A'}")
    except Exception as e:
        report("Search no match", False, str(e))

    # 3. Search with missing tags param
    try:
        status, data = api_get("/api/artifacts/registry/search")
        report("Search handles missing tags param",
               status == 200 and isinstance(data, list), f"status={status}")
    except Exception as e:
        report("Search missing param", False, str(e))

    # 4. Search with empty tags
    try:
        status, data = api_get("/api/artifacts/registry/search?tags=")
        report("Search handles empty tags",
               status == 200 and isinstance(data, list) and len(data) == 0, f"status={status}")
    except Exception as e:
        report("Search empty tags", False, str(e))

    print("\n── Versions API ──")

    # 5. Versions for nonexistent artifact (GET endpoint)
    try:
        status, _ = api_get("/api/artifacts/registry/nonexistent-xyz/versions")
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        report("Versions 404", False, str(e))
        status = None
    if status is not None:
        report("Versions 404 for nonexistent artifact", status == 404, f"status={status}")

    # 6. Registry list
    try:
        status, data = api_get("/api/artifacts/registry")
        report("Registry list returns array",
               status == 200 and isinstance(data, list),
               f"status={status}, type={type(data).__name__}")

        # 7. If artifacts exist, test versions endpoint
        if isinstance(data, list) and len(data) > 0:
            name = data[0].get("name", "")
            st2, ver_data = api_get(f"/api/artifacts/registry/{name}/versions")
            report(f"Versions returns data for '{name}'",
                   st2 == 200, f"status={st2}")
        else:
            skip("Versions for existing artifact", "no artifacts in registry")
    except Exception as e:
        report("Registry list", False, str(e))

    print("\n── Assistant Query Model ──")

    # 8. Query accepts active_artifact
    try:
        status = api_post("/api/assistant/query", {
            "query": "test",
            "active_artifact": {"name": "test-artifact"}
        })
        report("Query accepts active_artifact field",
               status != 422, f"status={status}")
    except Exception as e:
        report("Query active_artifact", False, str(e))

    # ── UI Tests (Playwright) ──────────────────────────────────

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        ctx.set_default_timeout(15000)
        ctx.add_init_script("""
            localStorage.setItem('shadowbroker_onboarding_complete', 'true');
            localStorage.setItem('shadowbroker_changelog_v0.9.5', 'true');
        """)
        page = ctx.new_page()

        print("\n=== Loading dashboard ===")
        try:
            page.goto("http://localhost:3000", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("text=S H A D O W", timeout=15000)
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"FATAL: Could not load dashboard — {e}")
            browser.close()
            return

        print("\n── AI Panel + Artifact Browser UI ──")

        # 9. Open AI panel via ANALYST toggle
        try:
            # The AI toggle is: div.cursor-pointer > div "ANALYST" + div "AI"/"OPEN"
            analyst_toggle = page.locator("div.cursor-pointer:has(div:text('ANALYST'))").first
            analyst_toggle.click()
            page.wait_for_timeout(1500)

            ai_panel = page.locator("text=AI ANALYST")
            report("AI panel opens via ANALYST toggle",
                   ai_panel.count() > 0,
                   f"found={ai_panel.count()}")

            if ai_panel.count() > 0:
                # 10. Artifacts browser button
                layers_btn = page.locator("button[title='Browse artifacts']")
                report("Artifacts browser button exists",
                       layers_btn.count() > 0,
                       f"found={layers_btn.count()}")

                if layers_btn.count() > 0:
                    # 11. Click and verify artifacts mode
                    layers_btn.click()
                    page.wait_for_timeout(1500)

                    artifacts_label = page.locator("text=ARTIFACTS")
                    report("Artifacts browser mode opens",
                           artifacts_label.count() > 0,
                           f"found={artifacts_label.count()}")

                    # Check for content or empty state
                    page.wait_for_timeout(1000)
                    has_content = (
                        page.locator("text=NO ARTIFACTS IN REGISTRY").count() > 0 or
                        page.locator("text=LOADING REGISTRY").count() > 0 or
                        # Artifact entries show title text
                        page.locator("span.font-semibold").count() > 0
                    )
                    report("Artifacts browser shows content or empty state",
                           has_content,
                           "neither list nor empty state found" if not has_content else "")
                else:
                    skip("Artifacts browser mode", "button not found")
                    skip("Artifacts browser content", "button not found")
            else:
                skip("Artifacts browser button", "AI panel not open")
                skip("Artifacts browser mode", "AI panel not open")
                skip("Artifacts browser content", "AI panel not open")

        except Exception as e:
            report("AI panel / artifact browser", False, f"{e}")

        # ── Regression checks ──────────────────────────────────

        print("\n── Regression checks ──")

        # 12. Health endpoint (via frontend proxy)
        try:
            resp = page.request.get("http://localhost:3000/api/health")
            report("Health endpoint via proxy returns 200",
                   resp.status == 200, f"status={resp.status}")
        except Exception as e:
            report("Health proxy", False, str(e))

        # 13. Artifact 404
        try:
            resp = page.request.get("http://localhost:3000/api/artifacts/nonexistent-id")
            report("Artifact 404 for unknown ID",
                   resp.status == 404, f"status={resp.status}")
        except Exception as e:
            report("Artifact 404", False, str(e))

        # 14. Console errors
        try:
            errors = []
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            critical = [e for e in errors if "FATAL" in e or "Uncaught" in e or "TypeError" in e.split(":")[0]]
            report("No critical JS errors after reload",
                   len(critical) == 0,
                   f"{len(critical)} critical errors: {critical[:3]}" if critical else "")
        except Exception as e:
            report("Console errors check", False, str(e))

        browser.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  Artifact Evolution E2E Tests (Steps 4-6)")
    print("=" * 60)
    run_tests()
    print(f"\n{'=' * 60}")
    print(f"  Results: {PASS} passed, {FAIL} failed, {SKIP} skipped")
    print(f"{'=' * 60}")
    if ERRORS:
        print("\nFailures:")
        for name, detail in ERRORS:
            print(f"  • {name}: {detail}")
    sys.exit(1 if FAIL > 0 else 0)
