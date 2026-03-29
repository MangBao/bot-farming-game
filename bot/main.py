"""
main.py – Entry point for the Target Games automation bot.

Responsibilities:
    • Initialise the Playwright browser (Chromium, headless=False)
    • Call login_and_navigate() once at startup
    • Run the infinite farming loop via run_bot()

Import map (no circular dependencies):
    config  ← (no local imports)
    utils   ← config
    auth    ← config, utils
    captcha ← config, utils
    scanner ← config, utils, captcha
    combat  ← config, utils, scanner
    main    ← config, utils, auth, scanner, combat
"""

import time
import logging
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

import config
from utils import random_delay, send_telegram_notification
from auth import login_and_navigate
from scanner import scan_pokemon
from combat import handle_encounter

log = logging.getLogger(__name__)


# ===========================================================================
# Bot main loop
# ===========================================================================

def run_bot(page: Page) -> None:
    """
    Continuous farming loop:
      1. scan_pokemon()      – look for a wild Pokémon
      2. handle_encounter()  – flee or fight/catch
      3. random_delay()      – human-like pause
      repeat forever.

    Recovery policy:
        TimeoutError → page.reload()
        After MAX_ERRORS_BEFORE_RELOGIN consecutive errors → full re-login
        KeyboardInterrupt → graceful shutdown
    """
    consecutive_errors = 0
    loop_count         = 0

    log.info("[bot] ══════════════════════════════════════")
    log.info("[bot]  Target Bot started – entering main loop")
    log.info("[bot] ══════════════════════════════════════")

    while True:
        loop_count += 1
        log.info("[bot] ── Loop #%d ──", loop_count)

        try:
            # ── Scan ─────────────────────────────────────────────────────────
            pokemon = scan_pokemon(page)

            if pokemon:
                log.info(
                    "[bot] Found: %s | Rank: %s | HP: %d/%d",
                    pokemon["name"], pokemon["rank"],
                    pokemon["current_hp"], pokemon["max_hp"],
                )
                random_delay()
                caught_ball = handle_encounter(page, pokemon)
                if caught_ball:
                    log.info("[bot] 🏆 Caught %s! Resuming scan.", pokemon["name"])
                    
                    if pokemon["rank"] in config.HIGH_VALUE_RANKS:
                        hp_str = f"{pokemon['current_hp']}/{pokemon['max_hp']}"
                        send_telegram_notification(
                            pokemon["name"], 
                            pokemon["rank"], 
                            hp_str, 
                            used_ball=caught_ball, 
                            image_url=pokemon.get("image_url")
                        )
                        log.info("[bot] 📱 Đã gửi thông báo Telegram cho %s!", pokemon["name"])
                else:
                    log.info("[bot] 🔄 Encounter ended (fled/miss/skipped). Back to scan.")
            else:
                log.info("[bot] No Pokémon this round – waiting before retry.")
                random_delay(config.RETRY_DELAY_MIN, config.RETRY_DELAY_MAX)

            # Reset error counter on any successful iteration
            consecutive_errors = 0
            random_delay()

        # ── Recoverable: timeout / stuck UI ──────────────────────────────────
        except PlaywrightTimeoutError as exc:
            consecutive_errors += 1
            log.warning(
                "[bot] ⚠️  TimeoutError (error #%d/%d): %s",
                consecutive_errors, config.MAX_ERRORS_BEFORE_RELOGIN, exc,
            )

            if consecutive_errors >= config.MAX_ERRORS_BEFORE_RELOGIN:
                log.warning("[bot] Too many consecutive errors – re-logging in...")
                try:
                    login_and_navigate(page)
                    consecutive_errors = 0
                except Exception as login_exc:  # pylint: disable=broad-except
                    log.error("[bot] Re-login also failed: %s", login_exc, exc_info=True)
                    log.info("[bot] Waiting 15s before next attempt...")
                    time.sleep(15)
            else:
                log.info("[bot] Reloading page and retrying...")
                try:
                    page.reload(wait_until="domcontentloaded", timeout=30_000)
                    page.wait_for_load_state("networkidle", timeout=20_000)
                    log.info("[bot] Page reloaded. Resuming loop.")
                except Exception as reload_exc:  # pylint: disable=broad-except
                    log.error("[bot] Reload failed: %s", reload_exc)
                random_delay(config.RETRY_DELAY_MIN, config.RETRY_DELAY_MAX)

        # ── Graceful stop via Ctrl+C ──────────────────────────────────────────
        except KeyboardInterrupt:
            log.info("[bot] ⛔ Interrupted by user – stopping bot.")
            break

        # ── Catch-all: log and continue ───────────────────────────────────────
        except Exception as exc:  # pylint: disable=broad-except
            consecutive_errors += 1
            log.error(
                "[bot] Unexpected error (#%d): %s",
                consecutive_errors, exc, exc_info=True,
            )
            log.info("[bot] Sleeping 10s before continuing...")
            time.sleep(10)


# ===========================================================================
# Entry point
# ===========================================================================

def main() -> None:
    log.info("[main] Launching Chromium...")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,           # set True to run silently
            slow_mo=300,              # slight base delay for UI stability
            args=["--start-maximized"],
        )
        context = browser.new_context(no_viewport=True)
        page    = context.new_page()

        try:
            login_and_navigate(page)
            run_bot(page)             # ← enters the infinite loop

        except Exception as exc:      # pylint: disable=broad-except
            log.error("[main] Fatal error: %s", exc, exc_info=True)

        finally:
            log.info("[main] Closing browser.")
            try:
                if 'context' in locals():
                    context.close()
                if 'browser' in locals():
                    browser.close()
            except (KeyboardInterrupt, Exception):
                # Bỏ qua các lỗi liên quan đến việc Playwright bị ngắt đột ngột
                pass


if __name__ == "__main__":
    main()
