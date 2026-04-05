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
import sys
import os
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

import subprocess
import config
from utils import (
    random_delay, 
    random_sleep, 
    send_telegram_notification, 
    send_telegram_alert, 
    send_telegram_reply,
    start_telegram_listener,
    is_special_variant,
    load_special_pokemon
)
from auth import login_and_navigate, auto_login, check_map_locked
from scanner import scan_pokemon, scrape_special_pokemon_from_ui
from combat import handle_encounter, flee

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
        
        if config.BOT_STATE.get("is_paused"):
            if loop_count % 10 == 1:
                log.info("[bot] ⏸️  Bot is currently PAUSED via Telegram. Waiting...")
            time.sleep(3)
            continue

        log.info("[bot] ── Loop #%d ──", loop_count)

        # ── Remote Map Switch Check ──────────────────────────────────
        if config.BOT_STATE.get("change_map_to"):
            new_map_slug = config.BOT_STATE["change_map_to"]
            target_url = f"{config.BASE_URL}/map/{new_map_slug}"
            
            log.info(f"[bot] Nhận lệnh Telegram: Chuyển vùng sang {target_url}")
            try:
                page.goto(target_url, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=20_000)
                log.info(f"[bot] Chuyển map thành công: {new_map_slug}")
                
                # Cập nhật TARGET_MAP để đồng bộ hệ thống (dùng cho lệnh /learn và kiểm tra pet đặc biệt)
                config.TARGET_MAP = new_map_slug
                
                # Check if the map we just jumped to is actually locked
                if check_map_locked(page):
                    log.error("[bot] Lệnh chuyển map thất bại do Map bị khóa.")
                    # We don't exit here to allow user to try another map via Telegram
                else:
                    send_telegram_reply(f"✅ <b>Hạ cánh an toàn tại {new_map_slug.replace('-', ' ').title()}!</b>\nTiến hành quét khu vực mới...")
            except Exception as e:
                log.error(f"[bot] Lỗi khi chuyển vùng: {e}")
                send_telegram_reply(f"❌ <b>Lỗi khi chuyển vùng:</b> <code>{str(e)}</code>")
            finally:
                config.BOT_STATE["change_map_to"] = None
                continue # Restart loop to begin scanning new map immediately

        # ── Auto-Recovery Check ──────────────────────────────────────
        if not auto_login(page):
            send_telegram_alert("🚨 Bot bị kẹt ở màn hình Đăng nhập hoặc mất kết nối!")
            log.error("[bot] Lỗi nghiêm trọng: Không thể tự đăng nhập lại. Dừng bot.")
            break

        try:
            # ── Learn Map Flag Check (Triggered via Telegram) ────────────────
            if config.BOT_STATE.get("trigger_learn_map"):
                log.info(f"[bot] Tiến hành học Pokémon đặc biệt từ UI tại {config.TARGET_MAP}...")
                learned_list = scrape_special_pokemon_from_ui(page, config.TARGET_MAP)
                config.BOT_STATE["trigger_learn_map"] = False
                
                if learned_list:
                    learned_str = ", ".join(learned_list)
                    send_telegram_reply(f"✅ <b>Đã học xong!</b>\n\n📌 <b>Hệ thống đã nhận diện các Pokémon đặc biệt tại {config.TARGET_MAP}:</b>\n<code>{learned_str}</code>")
                else:
                    send_telegram_reply("❌ <b>Học thất bại!</b> Không tìm thấy danh sách Pokémon Đặc biệt tại đây hoặc lỗi UI.")

            # ── Scan ─────────────────────────────────────────────────────────
            pokemon = scan_pokemon(page)
            if pokemon:
                # Nạp danh sách đặc biệt động từ JSON với cấu trúc 'maps'
                all_special_data = load_special_pokemon()
                # Kiểm tra pet đặc biệt trong đúng map đang đứng
                current_map_special_list = all_special_data.get("maps", {}).get(config.TARGET_MAP, [])
                
                # Lấy tên và Rank để kiểm tra điều kiện
                pkm_name_upper = pokemon['name'].upper()
                is_vip         = pokemon["rank"] in config.ALWAYS_CATCH_RANKS
                is_new         = pokemon.get("is_new_pokedex", False)
                is_special     = is_special_variant(pokemon["name"])
                is_must_catch  = pkm_name_upper in current_map_special_list

                if is_must_catch or is_vip or is_new or is_special:
                    if is_must_catch:
                        log.info(f"[bot] 🚨 MỤC TIÊU ĐẶC BIỆT: {pkm_name_upper}! Tiến hành bắt ngay lập tức.")
                    else:
                        log.info(f"[bot] Phát hiện Pokemon cần bắt (VIP/New/Variant): {pkm_name_upper}. Tiến hành ép máu...")
                    
                    random_delay()
                    caught_ball = handle_encounter(page, pokemon, intent="catch")
                else:
                    # Xử lý Pokemon đã có trong Pokedex
                    if config.AUTO_KILL_DUPLICATES:
                        log.info(f"[bot] {pkm_name_upper} đã có trong Pokedex. Chế độ: TIÊU DIỆT (Cày xu).")
                        random_delay()
                        caught_ball = handle_encounter(page, pokemon, intent="kill")
                    else:
                        log.info(f"[bot] {pkm_name_upper} đã có trong Pokedex. Chế độ: BỎ QUA (Tiết kiệm thời gian).")
                        flee(page)
                        caught_ball = ""
                
                if caught_ball:
                    log.info("[bot] 🏆 Caught %s! Resuming scan.", pokemon["name"])
                    hp_str = f"{pokemon['current_hp']}/{pokemon['max_hp']}"
                    send_telegram_notification(
                        pokemon_name=pokemon["name"], 
                        rank=pokemon["rank"], 
                        hp=hp_str, 
                        used_ball=caught_ball, 
                        image_url=pokemon.get("image_url"),
                        is_new_pokedex=is_new,
                        is_special_variant=is_special,
                        is_must_catch=is_must_catch
                    )
                    log.info("[bot] 📱 Đã gửi thông báo Telegram cho %s!", pokemon["name"])
                else:
                    log.info("[bot] 🔄 Encounter ended (killed/fled/miss). Back to scan.")
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
    auth_path = "auth.json"
    
    # ── Step 0: Đảm bảo môi trường sạch ──────────────────────────────────────
    if os.path.exists(auth_path):
        log.info(f"[main] 🧹 Đang dọn dẹp file {auth_path} cũ...")
        try:
            os.remove(auth_path)
        except Exception as e:
            log.error(f"[main] Không thể xóa {auth_path}: {e}")

    # ── Step 1: Tự động tạo session mới ─────────────────────────────────────
    gen_script = os.path.join("tools", "generate_auth.py")
    log.info(f"[main] 🚀 Đang khởi chạy script tạo Auth: {gen_script}...")
    log.info("[main] Chú ý: Hãy hoàn tất đăng nhập trong cửa sổ trình duyệt vừa hiện ra.")
    
    try:
        # Sử dụng sys.executable để gọi đúng python hiện tại
        # Cửa sổ trình duyệt của script generate_auth.py sẽ hiện lên ở đây
        subprocess.run([sys.executable, gen_script], check=True)
    except subprocess.CalledProcessError:
        log.error("[main] ❌ Script generate_auth.py kết thúc với lỗi. Dừng bot.")
        return
    except Exception as e:
        log.error(f"[main] ❌ Lỗi không mong đợi khi chạy script tạo session: {e}")
        return

    # Kiểm tra file auth.json đã được tạo thành công chưa
    if not os.path.exists(auth_path):
        log.error(f"[main] ❌ Lỗi: File {auth_path} không được tạo. Bot không có phiên để chạy.")
        return

    log.info("[main] ✨ Khởi tạo session thành công. Bắt đầu vào game...")
    
    # ── Step 2: Khởi chạy Bot chính ──────────────────────────────────────────
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,           # set True to run silently
            slow_mo=300,              # slight base delay for UI stability
            args=["--start-maximized"],
        )
        
        context_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {'width': 1920, 'height': 1080},
            "storage_state": auth_path
        }
        
        context = browser.new_context(**context_args)
        page    = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            log.info("[main] Bắt đầu luồng lắng nghe Telegram ngầm...")
            start_telegram_listener()
            
            # 2. Nhảy thẳng vào map (vì session luôn được khởi tạo mới ở bước trên)
            login_and_navigate(page, skip_login_fields=True)
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
