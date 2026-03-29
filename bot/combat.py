"""
combat.py – Encounter handling: flee, attack, throw ball, capture result check.

Contains:
    • _flee(page)
    • _attack(page)
    • _select_and_throw_ball(page, rank)  → bool
    • _check_capture_result(page)         → str  ('success' | 'fled' | 'miss')
    • handle_encounter(page, pokemon_data)  → bool
"""

import re
import logging
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

import config
from utils import random_delay, random_sleep, send_telegram_alert
from scanner import _parse_hp_from_page

log = logging.getLogger(__name__)


# ===========================================================================
# Private action helpers
# ===========================================================================

def _flee(page: Page) -> None:
    """Click 'Bỏ chạy' and wait for the encounter screen to close."""
    log.info("[flee] Fleeing encounter...")
    random_delay()
    try:
        flee_btn = page.get_by_role("button", name="Bỏ chạy")
        flee_btn.wait_for(state="visible", timeout=10_000)
        flee_btn.click()
        page.get_by_role("button", name="Tìm kiếm").wait_for(state="visible", timeout=10_000)
        log.info("[flee] Fled successfully.")
    except PlaywrightTimeoutError:
        log.error("[flee] 'Bỏ chạy' or 'Tìm kiếm' not found or timed out.")


def _attack(page: Page) -> None:
    """Click the attack / damage move button."""
    random_delay()
    try:
        for label in ("Chiến đấu", "Tấn công", "Attack"):
            btn = page.get_by_role("button", name=label)
            if btn.is_visible(timeout=3_000):
                btn.click()
                log.info("[attack] Clicked '%s'.", label)
                return
        log.warning("[attack] Named button not found – clicking first button.")
        page.locator("button").first.click()
    except PlaywrightTimeoutError:
        log.error("[attack] Attack button not found within timeout.")


def _select_and_throw_ball(page: Page, rank: str) -> str:
    """
    Open Pokéball dropdown, pick the best ball based on rank, click 'Dùng bóng'.

    Returns:
        String name of the ball used (e.g. "PokeBall", "MasterBall") 
        or empty string if action failed.
    """
    log.info("[ball] Opening Pokéball selector...")
    random_delay()

    # ── Locate dropdown ──────────────────────────────────────────────────────
    try:
        dropdown = page.locator("select").filter(has_text="Chọn bóng để bắt").first
        if not dropdown.is_visible(timeout=2_000):
            dropdown = page.locator("select").first

        dropdown.wait_for(state="visible", timeout=10_000)
    except PlaywrightTimeoutError:
        log.error("[ball] Pokéball dropdown not found.")
        return ""

    # ── Target Ball mapping ──────────────────────────────────────────────────
    target_balls = []
    if rank in ["GOD", "GR", "MR", "LR", "UR+", "UR", "SSR", "SSS+", "SSS", "SS"]:
        target_balls = ["Master", "Ultra"]
    elif rank in ["SR", "R", "S", "A"]:
        target_balls = ["Ultra", "Great"]
    else:
        target_balls = ["PokeBall", "Great"]

    # ── Parse options ────────────────────────────────────────────────────────
    pct_re       = re.compile(r"(\d+(?:\.\d+)?)\s*%")
    best_value   = ""
    best_pct     = -1.0
    best_name    = "PokeBall"
    target_value = ""
    target_name  = ""

    def normalize_ball_name(raw: str) -> str:
        r = raw.lower()
        if "master" in r: return "MasterBall"
        if "ultra" in r:  return "Ultra Ball"
        if "great" in r:  return "Great Ball"
        return "PokeBall"

    tag = dropdown.evaluate("el => el.tagName.toLowerCase()")

    if tag == "select":
        options = dropdown.locator("option").all()
        
        # ── Parse inventory and filter available options ──────────────────────
        count_re = re.compile(r"\(x(\d+)\)")
        available_options = [] # list of (name, value, count, pct)
        
        for opt in options:
            text = opt.inner_text()
            val = opt.get_attribute("value") or text.strip()
            
            p_match = pct_re.search(text)
            c_match = count_re.search(text)
            
            pct = float(p_match.group(1)) if p_match else 0.0
            count = int(c_match.group(1)) if c_match else 0
            name = normalize_ball_name(text)
            
            log.info("[ball]   Option: '%-30s' → %.1f%% | Count: %d", text.strip(), pct, count)
            if count > 0:
                available_options.append((name, val, count, pct))
                if pct > best_pct:
                    best_pct = pct
                    best_value = val
                    best_name = name

        # ── Selection Logic ──────────────────────────────────────────────────
        chosen_ball_val = ""
        chosen_ball_name = ""
        
        # Try target balls in order of preference
        for t_ball in target_balls:
            for opt_name, opt_val, opt_count, opt_pct in available_options:
                if t_ball.lower() in opt_name.lower():
                    chosen_ball_val = opt_val
                    chosen_ball_name = opt_name
                    log.info("[ball] Selected target ball: %s (x%d)", opt_name, opt_count)
                    break
            if chosen_ball_val:
                break
                
        # ── Emergency Check for VIPs ──────────────────────────────────────────
        if rank in config.ALWAYS_CATCH_RANKS:
            # Check if we have high-tier balls (Master or Ultra)
            has_high_tier = any("master" in opt[0].lower() or "ultra" in opt[0].lower() for opt in available_options)
            
            if not has_high_tier:
                log.warning("[ball] 🚨 VIP ENCOUNTER & NO HIGH-TIER BALLS!")
                send_telegram_alert(f"🚨 KHẨN CẤP: Gặp {rank} VIP nhưng đã hết sạch bóng xịn (Master/Ultra)! Hãy vào game cứu ngay!")
                log.info("[ball] Tạm dừng 45 giây chờ cứu viện...")
                random_sleep(30, 60)
                # After waiting, we refresh options or just use what we have? 
                # To be safe, let's just proceed with best available if user didn't act
        
        if not chosen_ball_val and best_value:
            log.info("[ball] Preferred balls out of stock. Using best available: %s", best_name)
            chosen_ball_val = best_value
            chosen_ball_name = best_name
            
        if chosen_ball_val:
            dropdown.select_option(value=chosen_ball_val)
            chosen_ball = chosen_ball_name
        else:
            log.warning("[ball] No balls left in inventory!")
            return ""
    else:
        # Custom dropdown: click to open, then pick highest-%/target
        dropdown.click()
        page.wait_for_timeout(500)
        items       = page.locator("[class*=ball-option], [class*=pokeball-item], [role='option']").all()
        best_item   = None
        target_item = None

        for item in items:
            text = item.inner_text()
            m    = pct_re.search(text)
            if m:
                pct = float(m.group(1))
                log.info("[ball]   Option: '%-30s' → %.1f%%", text.strip(), pct)
                if pct > best_pct:
                    best_pct  = pct
                    best_item = item
                    best_name = normalize_ball_name(text)

        for t_ball in target_balls:
            for item in items:
                text = item.inner_text()
                if t_ball.lower() in text.lower():
                    target_item = item
                    target_name = normalize_ball_name(text)
                    log.info("[ball] Found target ball '%s'", t_ball)
                    break
            if target_item:
                break

        final_item = target_item or best_item
        chosen_ball = target_name if target_item else best_name

        if final_item is not None:
            if final_item == best_item and not target_item:
                log.info("[ball] Target ball not found, clicking best option (%.1f%%).", best_pct)
            else:
                log.info("[ball] Clicking selected ball option.")
            random_delay()
            final_item.click()
        else:
            log.warning("[ball] No option with parseable %% found – aborting throw.")
            return ""

    # ── Confirm throw ────────────────────────────────────────────────────────
    random_delay()
    log.info("[ball] Clicking 'Dùng bóng'...")
    try:
        confirm_btn = page.get_by_role("button", name="Dùng bóng")
        confirm_btn.wait_for(state="visible", timeout=10_000)
        confirm_btn.click()
        return chosen_ball
    except PlaywrightTimeoutError:
        log.error("[ball] 'Dùng bóng' button not found.")
        return ""


def _check_capture_result(page: Page) -> str:
    """
    Wait for the DOM to update after a ball throw and classify the outcome.

    Returns one of three string literals:
        'success'  – Pokémon was caught.
        'fled'     – Pokémon escaped / ran away (no more attempts possible).
        'miss'     – Ball failed but Pokémon is still in battle.
    """
    # Give animations / server response 2.5 s to settle
    page.wait_for_timeout(2_500)
    result_text = page.locator("body").inner_text()

    # ── State A: success ─────────────────────────────────────────────────────
    SUCCESS_KEYWORDS = (
        "Đã bắt được",          # Game chính: "Đã bắt được Slowking!"
        "Bắt thành công",
        "Chúc mừng",
        "caught", "success", "captured",
    )
    if any(kw in result_text for kw in SUCCESS_KEYWORDS):
        return "success"

    # ── State B: fled ────────────────────────────────────────────────────────
    FLED_KEYWORDS = (
        "Pokemon đã thoát khỏi bóng và bỏ chạy",  # Game chính: "(Đã thử 3/3 lần)"
        "thoát khỏi bóng",
        "escaped", "ran away", "fled",
    )
    if any(kw in result_text for kw in FLED_KEYWORDS):
        return "fled"

    # Extra fled check: HP bar / Pokémon sprite no longer visible
    hp_bar = page.locator(
        "[class*=hp-bar], [class*=health], [class*=pokemon-hp], [class*=hp]"
    ).first
    if not hp_bar.is_visible(timeout=1_000):
        log.warning("[ball] Không rõ trạng thái, thanh máu biến mất. Đã chụp ảnh lưu lại.")
        try:
            page.screenshot(path="debug_logs/unknown_fled.png", full_page=True)
        except Exception as e:
            log.error("[ball] Lỗi khi chụp ảnh: %s", e)
        return "fled"

    # ── State C: miss (still in battle) ─────────────────────────────────────
    return "miss"


# ===========================================================================
# Public encounter handler
# ===========================================================================

def handle_encounter(page: Page, pokemon_data: dict) -> str:
    """
    Decide whether to flee or fight, then manage the capture loop.

    Throwing logic:
        - Max 3 ball attempts (Pokémon flees after 3 misses).
        - Each attempt classifies the result as: success / fled / miss.
        - Returns True on capture, False on flee or exhausted attempts.

    Args:
        page         : Active Playwright page on the encounter screen.
        pokemon_data : Dict from scan_pokemon() {name, rank, current_hp, max_hp,
                       player_hp, player_max, is_new_pokedex}.

    Returns:
        String of the ball used (e.g. "PokeBall") if caught.
        Empty string "" if Pokémon fled or all attempts were exhausted.
    """
    name       = pokemon_data.get("name", "Unknown")
    rank       = pokemon_data.get("rank", "Unknown")
    current_hp = pokemon_data.get("current_hp", 0)
    max_hp     = pokemon_data.get("max_hp",     0)
    player_hp  = pokemon_data.get("player_hp",  0)
    player_max = pokemon_data.get("player_max", 0)
    is_new     = pokemon_data.get("is_new_pokedex", False)

    config.BOT_STATE["stats"]["encounters"] += 1
    if player_max > 0:
        config.BOT_STATE["player_hp"] = f"{player_hp}/{player_max}"

    log.info("[encounter] ─── %s | Rank: %s | HP: %d/%d ───", name, rank, current_hp, max_hp)

    # ── Self-Defense Check (entry) ────────────────────────────────────────────
    if player_max > 0 and (player_hp / player_max) < 0.15:
        log.warning(
            "[encounter] 🚨 BÁO ĐỘNG! Máu phe mình quá yếu (%.1f%%). Bỏ chạy để bảo toàn!",
            (player_hp / player_max) * 100
        )
        _flee(page)
        return ""

    # ── Smart Rank Gate ───────────────────────────────────────────────────────
    if rank not in config.ALWAYS_CATCH_RANKS:
        if is_new:
            log.info("[encounter] 🌟 POKEMON MỚI (Rank %s)! Bỏ qua lọc Rank, tiến hành bắt.", rank)
        else:
            log.info("[encounter] Rank '%s' đã có trong Pokedex → Bỏ chạy để tiết kiệm bóng.", rank)
            _flee(page)
            return ""
    else:
        log.info("[encounter] 🎯 Hàng VIP Rank '%s' – Tiến hành bắt.", rank)

    # ── Edge case: HP unreadable → skip weakening, throw immediately ──────────
    if max_hp == 0:
        log.warning("[encounter] max_hp=0, skipping combat – throwing ball now.")
    else:
        # ── Combat loop: Dynamic damage tracking with log parser ──────────────
        SAFE_HP_MARGIN       = 15    # Never attack below this absolute HP
        estimated_max_damage = 0

        for round_num in range(1, config.MAX_ATTACK_ROUNDS + 1):
            hp_pct            = current_hp / max_hp
            predicted_max_hit = estimated_max_damage + 5    # +5 buffer for crit variance

            log.info(
                "[encounter] Round %2d | HP %d/%d (%.1f%%) | Est.MaxDmg: %d | PredictedHit: %d",
                round_num, current_hp, max_hp, hp_pct * 100,
                estimated_max_damage, predicted_max_hit
            )

            # ── SAFETY STOP: absolute floor check ────────────────────────────
            if current_hp <= SAFE_HP_MARGIN:
                log.info(
                    "[encounter] ⚠️ Máu rớt vào vùng nguy hiểm (HP hiện tại: %d, "
                    "Có thể sốc damage: %d). Dừng đánh, ném bóng!",
                    current_hp, predicted_max_hit
                )
                break

            # ── SAFETY STOP: predictive kill check ───────────────────────────
            if estimated_max_damage > 0 and current_hp <= predicted_max_hit:
                log.info(
                    "[encounter] ⚠️ Máu rớt vào vùng nguy hiểm (HP hiện tại: %d, "
                    "Có thể sốc damage: %d). Dừng đánh, ném bóng!",
                    current_hp, predicted_max_hit
                )
                break

            # ── SAFETY STOP: Check if player fainted ─────────────────────────
            attack_btn = page.get_by_role("button", name=re.compile("Chiến đấu|Tấn công|Attack", re.I))
            if not attack_btn.is_visible(timeout=3_000) or not attack_btn.is_enabled():
                 log.warning("[encounter] 🚨 BÁO ĐỘNG: Nút chiến đấu biến mất/vô hiệu hóa! Pokemon phe mình đã kiệt sức.")
                 send_telegram_alert(f"🚨 BÁO ĐỘNG: Pokemon của bạn đã kiệt sức (Hết HP) khi đang đánh {name}! Bot tạm dừng chiến đấu.")
                 _flee(page)
                 return ""

            # ── Attack ───────────────────────────────────────────────────────
            log.info("[encounter] Attacking...")
            _attack(page)
            page.wait_for_timeout(1_500)

            # ── Read damage from combat log (primary source) ──────────────────
            body_text = page.locator("body").inner_text()
            dmg_match = re.search(r"Gây (\d+) sát thương!", body_text)
            if dmg_match:
                damage_dealt = int(dmg_match.group(1))
                log.info("[encounter] 📋 Log damage read: %d", damage_dealt)
            else:
                damage_dealt = None
                log.debug("[encounter] No 'Gây X sát thương!' found – using HP fallback.")

            # ── Refresh HP values (always needed) ────────────────────────────
            new_hp, new_max, new_p_hp, new_p_max = _parse_hp_from_page(page)
            if new_hp == 0 and new_max == 0:
                log.warning("[encounter] HP unreadable – Pokémon may have fainted.")
                return ""

            # Self-defense check mid-combat
            if new_p_max > 0 and (new_p_hp / new_p_max) < 0.15:
                log.warning(
                    "[encounter] 🚨 BÁO ĐỘNG! Phe mình máu dưới 15%% (%.1f%%). Chạy ngay đi!",
                    (new_p_hp / new_p_max) * 100
                )
                _flee(page)
                return ""

            # Compute damage_dealt from HP diff if log parse failed
            if damage_dealt is None:
                damage_dealt = current_hp - new_hp
                log.info("[encounter] 📋 Fallback HP-diff damage: %d", damage_dealt)

            current_hp = new_hp
            max_hp     = new_max

            # ── Update estimated max damage ───────────────────────────────────
            if damage_dealt > 0:
                estimated_max_damage = max(estimated_max_damage, damage_dealt)
                log.info("[encounter] Updated estimated_max_damage: %d", estimated_max_damage)
            else:
                log.info("[encounter] Đánh hụt/Máu không đổi, tiếp tục cẩn thận.")
        else:
            log.warning(
                "[encounter] Max attack rounds (%d) reached – proceeding to throw anyway.",
                config.MAX_ATTACK_ROUNDS,
            )

    # ── Capture loop: up to 3 attempts ───────────────────────────────────────
    MAX_THROWS = 3
    for attempt in range(MAX_THROWS):
        log.info("[encounter] 🎳 Throw attempt %d / %d", attempt + 1, MAX_THROWS)

        thrown = _select_and_throw_ball(page, rank)
        if not thrown:
            log.error("[encounter] Throw failed (could not interact with UI) – aborting.")
            return ""

        outcome = _check_capture_result(page)

        if outcome == "success":
            config.BOT_STATE["stats"]["caught"] += 1
            log.info("[encounter] ✅ Đã bắt được %s!", name)
            return thrown

        if outcome == "fled":
            log.warning("[encounter] 💨 Pokemon đã chạy mất!")
            return ""

        # State C: miss, still in battle
        log.info("[encounter] ❌ Bắt trượt lần %d, thử lại...", attempt + 1)
        random_delay()

    # Loop exhausted
    log.warning("[encounter] 🚫 Hết lượt ném, trở về map.")
    return ""
