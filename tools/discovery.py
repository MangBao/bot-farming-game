"""
discovery.py – DOM trinh sát cho Target Games.

Mục đích:
    1. Login và vào map Johto.
    2. Chụp ảnh màn hình trước khi tìm kiếm  → debug_step1_map.png
    3. Bấm 'Tìm kiếm' và đợi DOM cập nhật.
    4. Dump toàn bộ HTML                      → dom_dump.html
    5. Chụp ảnh màn hình sau khi tìm kiếm    → debug_step2_result.png
"""

import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("discovery")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
load_dotenv()

EMAIL    = os.environ.get("GAME_EMAIL",    "YOUR_EMAIL")
PASSWORD = os.environ.get("GAME_PASSWORD", "YOUR_PASSWORD")

LOGIN_URL = "https://target.com/login"
MAP_URL   = "https://target.com/map/vung-johto"

OUT_DIR   = Path(__file__).parent.parent / "debug_logs"
OUT_DIR.mkdir(exist_ok=True)
STEP1_PNG = OUT_DIR / "debug_step1_map.png"
STEP2_PNG = OUT_DIR / "debug_step2_result.png"
DOM_DUMP  = OUT_DIR / "dom_dump.html"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _try_fill(page, selectors: list[str], value: str, label: str) -> bool:
    """Try a list of CSS/role selectors until one succeeds."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=3_000):
                loc.fill(value)
                log.info("[discovery] %s filled via '%s'.", label, sel)
                return True
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# Main discovery flow
# ---------------------------------------------------------------------------

def run_discovery() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=400,
            args=["--start-maximized"],
        )
        context = browser.new_context(no_viewport=True)
        page    = context.new_page()

        try:
            # ── Step 0: Login ────────────────────────────────────────────────
            log.info("[discovery] Opening login page: %s", LOGIN_URL)
            page.goto(LOGIN_URL, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle", timeout=20_000)
            time.sleep(1.5)

            # Email
            filled = _try_fill(page, [
                "input[type='email']",
                "input[name='email']",
                "input[name='username']",
                "input[placeholder*='email' i]",
                "input[placeholder*='tên' i]",
            ], EMAIL, "email")
            if not filled:
                log.warning("[discovery] Could not fill email – trying label approach.")
                page.get_by_label("Email", exact=False).fill(EMAIL)

            time.sleep(0.8)

            # Password
            filled = _try_fill(page, [
                "input[type='password']",
                "input[name='password']",
                "input[placeholder*='mật' i]",
            ], PASSWORD, "password")
            if not filled:
                log.warning("[discovery] Could not fill password – trying label approach.")
                page.get_by_label("Password", exact=False).fill(PASSWORD)

            time.sleep(0.8)

            # Login button (try multiple strategies)
            login_clicked = False
            for name_hint in ("Đăng Nhập", "Đăng nhập", "Login", "Sign in"):
                try:
                    btn = page.get_by_role("button", name=name_hint)
                    if btn.is_visible(timeout=2_000):
                        btn.click()
                        login_clicked = True
                        log.info("[discovery] Login button clicked via name '%s'.", name_hint)
                        break
                except Exception:
                    pass

            if not login_clicked:
                # Last-resort: first submit button
                page.locator("button[type='submit'], input[type='submit']").first.click()
                log.warning("[discovery] Used fallback submit button.")

            page.wait_for_load_state("networkidle", timeout=30_000)
            log.info("[discovery] Post-login URL: %s", page.url)

            # ── Step 1: Navigate to map ──────────────────────────────────────
            log.info("[discovery] Navigating to map: %s", MAP_URL)
            page.goto(MAP_URL, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle", timeout=30_000)
            time.sleep(2)   # let JS render the map UI

            # Screenshot 1
            page.screenshot(path=str(STEP1_PNG), full_page=True)
            log.info("[discovery] ✅ Screenshot 1 saved → %s", STEP1_PNG)

            # ── Step 2: Click 'Tìm kiếm' ────────────────────────────────────
            search_clicked = False
            for name_hint in ("Tìm kiếm", "Tìm Kiếm", "Search", "Khám phá"):
                try:
                    btn = page.get_by_role("button", name=name_hint)
                    if btn.is_visible(timeout=3_000):
                        btn.click()
                        search_clicked = True
                        log.info("[discovery] 'Tìm kiếm' clicked via name '%s'.", name_hint)
                        break
                except Exception:
                    pass

            if not search_clicked:
                log.warning("[discovery] Named search button not found.")

            # Wait for DOM to settle (captcha may appear – we just wait, no solving)
            log.info("[discovery] Waiting 5s for UI to update...")
            time.sleep(5)

            # ── Step 3: Dump HTML ────────────────────────────────────────────
            html_content = page.content()
            DOM_DUMP.write_text(html_content, encoding="utf-8")
            log.info("[discovery] ✅ DOM dump saved → %s", DOM_DUMP)
            log.info("[discovery]    File size: %.1f KB", len(html_content) / 1024)

            # Screenshot 2
            page.screenshot(path=str(STEP2_PNG), full_page=True)
            log.info("[discovery] ✅ Screenshot 2 saved → %s", STEP2_PNG)

        except PlaywrightTimeoutError as exc:
            log.error("[discovery] Timeout: %s", exc)
            # Still try to dump whatever is loaded
            try:
                page.screenshot(path=str(STEP2_PNG))
                DOM_DUMP.write_text(page.content(), encoding="utf-8")
                log.info("[discovery] Partial dump saved after timeout.")
            except Exception:
                pass

        except Exception as exc:
            log.error("[discovery] Unexpected error: %s", exc, exc_info=True)

        finally:
            log.info("[discovery] Closing browser.")
            context.close()
            browser.close()

    log.info("[discovery] Done. Files written:")
    for f in [STEP1_PNG, STEP2_PNG, DOM_DUMP]:
        size = f.stat().st_size if f.exists() else 0
        log.info("  %-40s %s", f.name, f"({size:,} bytes)" if size else "(not created)")


if __name__ == "__main__":
    run_discovery()
