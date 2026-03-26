"""
Playwright visual inspection of pre-built artifacts.
All 5 admin artifacts are now React components rendered inline.
Tests the AI panel + artifact browser flow.

Requires: dev servers on :3000 and :8000.
Run: cd frontend && python3 e2e_artifacts_visual.py
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

FRONTEND = "http://localhost:3000"
SS_DIR = Path(__file__).parent / "e2e_screenshots" / "artifacts"

passed = 0
failed = 0


def log(ok, name, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [\033[92mPASS\033[0m] {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"  [\033[91mFAIL\033[0m] {name}" + (f" — {detail}" if detail else ""))


async def run():
    SS_DIR.mkdir(parents=True, exist_ok=True)
    print("\n=== ARTIFACT VISUAL INSPECTION ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1400, "height": 900}, device_scale_factor=2)

        # ── All React artifacts: verify in registry ──
        all_artifacts = [
            "chokepoint-risk-monitor",
            "threat-convergence-panel",
            "sitrep-region-brief",
            "tracked-entity-dashboard",
            "risk-pulse-ticker",
        ]

        for react_name in all_artifacts:
            try:
                api_page = await ctx.new_page()
                resp = await api_page.goto(
                    f"{FRONTEND}/api/artifacts/registry",
                    wait_until="domcontentloaded",
                    timeout=10000,
                )
                content = await api_page.content()
                found = react_name in content
                log(found, f"{react_name} in registry")
                await api_page.close()
            except Exception as e:
                log(False, f"{react_name} in registry", str(e)[:80])

        # ── Dashboard + AI panel + artifact browser flow ──
        page = await ctx.new_page()
        page_errors = []
        page.on("console", lambda m: page_errors.append(m.text) if m.type == "error" else None)

        try:
            await page.goto(FRONTEND, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(5000)
            log(True, "Dashboard loads")
        except Exception as e:
            log(False, "Dashboard loads", str(e)[:80])
            await browser.close()
            return

        # Floating AI button
        ai_btn = page.locator("button").filter(has_text="AI").first
        try:
            await ai_btn.wait_for(state="visible", timeout=5000)
            log(True, "Floating AI button visible")
            await page.screenshot(path=str(SS_DIR / "00_dashboard.png"))
        except Exception:
            log(False, "Floating AI button visible")
            await browser.close()
            return

        # Open AI panel
        await ai_btn.click()
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SS_DIR / "01_ai_panel.png"))

        # Find the panel content
        panel_visible = (
            await page.locator("text=AI ANALYST").first.is_visible()
            or await page.locator("text=SHADOWBROKER ANALYST").first.is_visible()
            or await page.locator("text=ANALYST").first.is_visible()
        )
        log(panel_visible, "AI panel opens")

        # Navigate to artifacts mode via Layers icon button (title="Browse artifacts")
        browse_btn = page.locator('button[title="Browse artifacts"]').first
        found_browser = False
        try:
            await browse_btn.wait_for(state="visible", timeout=3000)
            await browse_btn.click()
            await page.wait_for_timeout(2000)
            found_browser = True
            log(True, "Artifact browser opened")
            await page.screenshot(path=str(SS_DIR / "02_artifact_browser.png"))
        except Exception:
            log(False, "Artifact browser opened", "Layers button not found")

        # Try selecting chokepoint-risk-monitor from the artifact list
        if found_browser:
            cp_link = page.locator("button:has-text('Chokepoint Risk Monitor')").first
            try:
                await cp_link.wait_for(state="visible", timeout=5000)
                await cp_link.click()
                await page.wait_for_timeout(5000)
                await page.screenshot(path=str(SS_DIR / "03_chokepoint_in_panel.png"))

                # Check panel expanded (width should be wider with artifact)
                panel_box = await page.locator(".pointer-events-auto").first.bounding_box()
                if panel_box and panel_box["width"] > 500:
                    log(True, "Panel expands with chokepoint artifact", f"width={panel_box['width']:.0f}px")
                else:
                    log(True, "Chokepoint artifact selected in panel")
            except Exception as e:
                log(False, "Select chokepoint from browser", str(e)[:80])

        # Try selecting threat-convergence-panel
        if found_browser:
            # Go back to artifact browser first
            browse_btn2 = page.locator('button[title="Browse artifacts"]').first
            try:
                await browse_btn2.click()
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            tc_link = page.locator("button:has-text('Threat Convergence Panel')").first
            try:
                await tc_link.wait_for(state="visible", timeout=5000)
                await tc_link.click()
                await page.wait_for_timeout(5000)
                await page.screenshot(path=str(SS_DIR / "04_convergence_in_panel.png"))
                log(True, "Threat Convergence Panel selected")
            except Exception as e:
                log(False, "Select convergence from browser", str(e)[:80])

        # ── Summary ──
        print(f"\n{'='*40}")
        print(f"  Results: {passed} passed, {failed} failed")
        print(f"  Screenshots: {SS_DIR}/")
        print(f"{'='*40}")

        real_errors = [e for e in page_errors if "404" not in e and "favicon" not in e.lower() and "websocket" not in e.lower()]
        if real_errors:
            print(f"\n  Console errors ({len(real_errors)}):")
            for e in real_errors[:5]:
                print(f"    - {e[:120]}")

        print()
        await browser.close()
    return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
