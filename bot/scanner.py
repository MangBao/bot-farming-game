"""
scanner.py – Wild Pokémon detection and data extraction.

Contains:
    • _parse_hp_from_page(page)  – re-read HP from DOM
    • scan_pokemon(page)         – click search, solve captcha, parse result
"""

import re
import logging
from typing import Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

import config
from utils import random_delay
from captcha import handle_math_captcha

log = logging.getLogger(__name__)


def _parse_hp_from_page(page: Page) -> tuple[int, int, int, int]:
    """
    Scrape the page body for HP patterns for both enemy (first) and player (second).
    Returns (enemy_cur, enemy_max, player_cur, player_max); 0 defaults if not found.
    """
    body_text  = page.locator("body").inner_text()
    
    matches = re.findall(r"HP\s*(?:\n|\r)?\s*(\d+)\s*/\s*(\d+)", body_text, re.IGNORECASE)
    
    if not matches:
        try:
            locators = page.locator("div:has(> span:text-is('HP'))").all()
            for loc in locators[:2]:
                if loc.is_visible(timeout=500):
                    m2 = re.search(r"(\d+)\s*/\s*(\d+)", loc.inner_text())
                    if m2:
                        matches.append((m2.group(1), m2.group(2)))
        except Exception:
            pass

    enemy_cur, enemy_max = 0, 0
    player_cur, player_max = 0, 0

    if len(matches) > 0:
        try:
            enemy_cur, enemy_max = int(matches[0][0]), int(matches[0][1])
        except ValueError:
            pass
    if len(matches) > 1:
        try:
            player_cur, player_max = int(matches[1][0]), int(matches[1][1])
        except ValueError:
            pass

    return enemy_cur, enemy_max, player_cur, player_max


def scan_pokemon(page: Page) -> Optional[dict]:
    """
    Click 'Tìm kiếm', wait for the result, parse wild Pokémon info.

    Returns:
        dict  – {name, rank, current_hp, max_hp}  when a Pokémon is found.
        None  – when the map reports 'Không tìm thấy Pokemon nào' or times out.
    """
    NO_POKEMON_TEXT = "Không tìm thấy Pokemon nào"

    # ── Click search ─────────────────────────────────────────────────────────
    log.info("[scan] Checking 'Tìm kiếm' button...")
    random_delay()
    search_btn = page.get_by_role("button", name="Tìm kiếm")
    search_btn.wait_for(state="visible", timeout=10_000)
    
    # Check if a battle is already in progress (search button disabled)
    if search_btn.is_enabled():
        search_btn.click()
        log.info("[scan] Search triggered.")

        # ── Handle math captcha (may or may not appear) ───────────────────────────
        captcha_solved = handle_math_captcha(page)
        if captcha_solved:
            log.info("[scan] Captcha solved – re-triggering search for reliable result...")
            random_delay(1.5, 2.5)
            # Re-click search because the game might not automatically load the encounter after captcha
            if search_btn.is_visible() and search_btn.is_enabled():
                search_btn.click()
                log.info("[scan] Search re-triggered after captcha.")
            else:
                log.warning("[scan] Search button not available after captcha - continuing anyway.")

        # ── Wait for scan result (captcha-aware) ──────────────────────────────────
        try:
            page.wait_for_function(
                """
                () => {
                    const body = document.body.innerText;
                    return body.includes('Không tìm thấy Pokemon nào')
                        || body.includes('hoang dã xuất hiện!')
                        || body.includes('Chiến đấu');
                }
                """,
                timeout=6_000,   # Set fixed 6s timeout for efficiency
            )
        except PlaywrightTimeoutError:
            log.warning("[scan] Scan result did not appear within 6s - skipping to next loop.")
            return None
    else:
        # User left an unfinished encounter – the UI shows it immediately
        log.info("[scan] Phát hiện trận chiến cũ đang dang dở, bỏ qua click tìm kiếm.")
        # We don't need to wait for dom updates since the UI is already describing the pokemon

    # ── Check 'no Pokémon' message ────────────────────────────────────────────
    page_text = page.locator("body").inner_text()
    if NO_POKEMON_TEXT in page_text:
        log.info("[scan] No wild Pokémon found this round.")
        return None

    is_new_pokedex = False
    try:
        # Check for both "CHƯA CÓ TRONG POKEDEX" and "NEW -" for maximum reliability
        is_new_pokedex = page.get_by_text("CHƯA CÓ TRONG POKEDEX").is_visible(timeout=500) or "CHƯA CÓ TRONG POKEDEX" in page_text or "NEW -" in page_text
    except Exception:
        if "CHƯA CÓ TRONG POKEDEX" in page_text or "NEW -" in page_text:
            is_new_pokedex = True
            
    if is_new_pokedex:
        log.info("[scan] 🌟 Found NEW Pokémon for Pokedex!")

    # ── Extract name and rank ────────────────────────────────────────────────
    name: str = "Unknown"
    rank: str = "Unknown"

    # The actual game text often looks like: 
    # "Một Snubbull - Fairy (Lvl 10) [D] hoang dã xuất hiện!"
    match = re.search(r"Một\s+([A-Za-z0-9_\-\s\']+?)\s+-.*?\[([A-Z0-9\+]+)\]\s*hoang dã", page_text)
    if match:
        name = match.group(1).strip()
        rank = match.group(2).upper().strip()
    else:
        # Fallback to the old rank token search if regex fails
        log.warning("[scan] Regex match failed! Fallback to plain text search.")
        for token in config.RANK_TOKENS:
            # We use \b boundary but adapted to not break on '+' at the end
            if token.endswith('+'):
                pat = rf"(?<![\w])({re.escape(token)})(?!\+)"
            else:
                pat = rf"(?<![\w\+])({re.escape(token)})(?![\w\+])"
            if re.search(pat, page_text):
                rank = token
                break

    log.info("[scan] Pokémon name: '%s'", name)
    log.info("[scan] Rank: %s", rank)

    # ── Extract image URL (for Telegram notification) ────────────────────────
    image_url = ""
    try:
        img_loc = page.locator("img.animate-bounce").first
        if not img_loc.is_visible(timeout=1000):
            img_loc = page.locator("div.absolute.inset-0 img").first
        if img_loc.is_visible():
            image_url = img_loc.get_attribute("src") or ""
    except Exception:
        pass

    # ── Extract HP ────────────────────────────────────────────────────────────
    enemy_cur, enemy_max, player_cur, player_max = _parse_hp_from_page(page)
    if enemy_max:
        log.info("[scan] Enemy HP: %d / %d | Player HP: %d / %d", enemy_cur, enemy_max, player_cur, player_max)
    else:
        log.warning("[scan] HP could not be parsed.")

    return {
        "name": name, 
        "rank": rank, 
        "current_hp": enemy_cur, 
        "max_hp": enemy_max,
        "player_hp": player_cur,
        "player_max": player_max,
        "is_new_pokedex": is_new_pokedex,
        "image_url": image_url
    }
