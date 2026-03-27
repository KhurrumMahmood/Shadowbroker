"""Playwright E2E tests for the /artifacts showcase page.

Tests:
1. Page loads with header and sidebar
2. Sidebar shows all registry artifacts grouped by category
3. Clicking a React artifact loads its preview and fixture data
4. Dataset selector shows the artifact's dataset label
5. Clicking an HTML artifact shows "REQUIRES BACKEND" and "Embedded in HTML"
6. Chat panel toggles on/off
7. Fake chat panel shows conversation messages
8. Re-clicking the same artifact doesn't flash loading spinner
9. Empty state shows when no artifact selected
10. "Dashboard" link navigates back to /

Run: cd frontend && python3 e2e_artifacts_list.py
Requires: dev server on :3000 (frontend).
"""
import sys
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
        page = ctx.new_page()

        print("\n=== Loading /artifacts ===")
        page.goto("http://localhost:3000/artifacts", wait_until="networkidle", timeout=30000)

        # ── Test 1: Page loads with header ──
        try:
            header = page.wait_for_selector("h1", timeout=10000)
            text = header.inner_text() if header else ""
            report("1. Header renders", "ARTIFACTS" in text and "SHOWCASE" in text, f"got: {text}")
        except Exception as e:
            report("1. Header renders", False, str(e))

        # ── Test 2: Sidebar shows artifacts grouped by category ──
        try:
            # Check category section headers exist
            sidebar_text = page.locator(".styled-scrollbar").first.inner_text()
            sidebar_upper = sidebar_text.upper()
            has_categories = (
                "RISK & MONITORING" in sidebar_upper
                or "THREAT ANALYSIS" in sidebar_upper
                or "ENTITY TRACKING" in sidebar_upper
            )
            # Count artifact buttons in the sidebar
            artifact_buttons = page.locator(".styled-scrollbar button").count()
            report(
                "2. Sidebar shows categorized artifacts",
                has_categories and artifact_buttons >= 6,
                f"categories={has_categories}, buttons={artifact_buttons}",
            )
        except Exception as e:
            report("2. Sidebar shows categorized artifacts", False, str(e))

        # ── Test 3: Empty state shows when no artifact selected ──
        try:
            empty_text = page.locator("text=Select an Artifact").first
            report("3. Empty state visible initially", empty_text.is_visible())
        except Exception as e:
            report("3. Empty state visible initially", False, str(e))

        # ── Test 4: Clicking a React artifact loads preview ──
        try:
            # Click the first React artifact via sidebar buttons
            sidebar_btns = page.locator(".styled-scrollbar button")
            sidebar_btns.first.click()
            # Wait for the artifact panel to render
            page.wait_for_timeout(3000)
            # Empty state should be gone
            empty_gone = not page.locator("text=Select an Artifact").is_visible()
            report("4. React artifact loads preview", empty_gone)
        except Exception as e:
            report("4. React artifact loads preview", False, str(e))

        # ── Test 5: Dataset selector shows the artifact's label ──
        try:
            selector = page.locator("select").first
            # The select should be visible and have at least one option
            is_visible = selector.is_visible()
            option_text = selector.locator("option").first.inner_text() if is_visible else ""
            report(
                "5. Dataset selector shows label",
                is_visible and len(option_text) > 0,
                f"option={option_text}",
            )
        except Exception as e:
            report("5. Dataset selector shows label", False, str(e))

        # ── Test 6: Fake chat panel shows messages ──
        try:
            # Chat should be visible by default
            ai_analyst = page.locator("text=AI Analyst").first
            demo_badge = page.locator("text=Demo").first
            chat_visible = ai_analyst.is_visible() and demo_badge.is_visible()
            # Should have multiple chat messages
            # Look for bot icons or user icons as message indicators
            messages_area = page.locator(".styled-scrollbar").nth(1)
            message_count = messages_area.locator("> div").count() if messages_area.is_visible() else 0
            report(
                "6. Fake chat panel with messages",
                chat_visible and message_count >= 2,
                f"visible={chat_visible}, messages={message_count}",
            )
        except Exception as e:
            report("6. Fake chat panel with messages", False, str(e))

        # ── Test 7: Chat toggle hides/shows chat panel ──
        try:
            # Find and click the Chat toggle button
            chat_toggle = page.locator("button:has-text('Chat')").first
            chat_toggle.click()
            page.wait_for_timeout(400)
            # AI Analyst header should be hidden
            chat_hidden = not page.locator("text=AI Analyst").first.is_visible()
            # Click again to restore
            chat_toggle.click()
            page.wait_for_timeout(400)
            chat_restored = page.locator("text=AI Analyst").first.is_visible()
            report(
                "7. Chat toggle hides/shows panel",
                chat_hidden and chat_restored,
                f"hidden={chat_hidden}, restored={chat_restored}",
            )
        except Exception as e:
            report("7. Chat toggle hides/shows panel", False, str(e))

        # ── Test 8: Clicking an HTML artifact shows appropriate labels ──
        try:
            # Find an HTML artifact (they have "REQUIRES BACKEND" label)
            html_btns = page.locator("button:has-text('REQUIRES BACKEND')")
            if html_btns.count() > 0:
                html_btns.first.click()
                page.wait_for_timeout(500)
                # Dataset selector should say "Embedded in HTML"
                embedded_text = page.locator("text=Embedded in HTML").first
                report(
                    "8. HTML artifact shows correct labels",
                    embedded_text.is_visible(),
                )
            else:
                skip("8. HTML artifact shows correct labels", "No HTML artifacts in sidebar")
        except Exception as e:
            report("8. HTML artifact shows correct labels", False, str(e))

        # ── Test 9: Re-click same artifact doesn't flash loading ──
        try:
            # Click a React artifact first
            sidebar_btns = page.locator(".styled-scrollbar button")
            sidebar_btns.first.click()
            page.wait_for_timeout(1500)
            # Click same artifact again
            sidebar_btns.first.click()
            # Check that loading overlay does NOT appear (re-click guard)
            page.wait_for_timeout(200)
            loading_visible = page.locator("text=LOADING FIXTURE DATA...").is_visible()
            report(
                "9. Re-click guard prevents loading flash",
                not loading_visible,
                f"loading_visible={loading_visible}",
            )
        except Exception as e:
            report("9. Re-click guard prevents loading flash", False, str(e))

        # ── Test 10: Dashboard link exists and points to / ──
        try:
            dash_link = page.locator("a:has-text('Dashboard')").first
            href = dash_link.get_attribute("href")
            report(
                "10. Dashboard link points to /",
                href == "/",
                f"href={href}",
            )
        except Exception as e:
            report("10. Dashboard link points to /", False, str(e))

        # ── Cleanup ──
        browser.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  ARTIFACTS LIST SHOWCASE — E2E TEST SUITE")
    print("=" * 60)
    try:
        run_tests()
    except Exception:
        traceback.print_exc()
        FAIL += 1

    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped")
    print(f"{'=' * 60}")
    if ERRORS:
        print("\n  FAILURES:")
        for name, detail in ERRORS:
            print(f"    {name}: {detail}")
    sys.exit(1 if FAIL > 0 else 0)
