"""
captcha.py – Math captcha detection and solving.

Contains:
    • _safe_calc(a, op, b)       – arithmetic without eval()
    • handle_math_captcha(page)  – detect dialog, solve, submit
"""

import re
import logging
from typing import Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

import config
from utils import random_delay

log = logging.getLogger(__name__)


def _safe_calc(a: int, op: str, b: int) -> Optional[int]:
    """
    Perform basic arithmetic safely without using eval().
    Returns None if the operator is unknown or division-by-zero occurs.
    """
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op in ("*", "x", "×"):
        return a * b
    if op in ("/", "÷"):
        if b == 0:
            log.error("[captcha] Division by zero in math problem.")
            return None
        return a // b   # integer division (game likely uses whole numbers)
    log.error("[captcha] Unknown operator: '%s'", op)
    return None


def handle_math_captcha(page: Page) -> bool:
    """
    Detect and solve the "XÁC MINH THAO TÁC" math captcha dialog that may
    appear after clicking 'Tìm kiếm'.

    Flow:
        1. Wait 1–1.5 s for the UI to settle.
        2. Check if "KIỂM TRA ANTI AUTO CLICK" text is visible.
        3. If NOT visible → return False (no captcha, carry on).
        4. If visible:
           a. Read the full question line via get_by_text("Mật mã Pokeball:").
           b. Regex-parse two integers and the operator.
           c. Compute result safely (no eval).
           d. Fill "Nhập kết quả" placeholder input.
           e. Click "Xác nhận" button.
           f. Random delay 1–2 s → return True.

    Returns:
        True  – captcha was detected and submitted.
        False – no captcha dialog found or an error occurred.
    """
    try:
        # Step 1: let the UI settle
        page.wait_for_timeout(1_200)

        # Step 2: detect dialog by its header text
        if not page.get_by_text("KIỂM TRA ANTI AUTO CLICK").is_visible(timeout=1_500):
            log.debug("[captcha] No captcha dialog visible.")
            return False

        log.info("[captcha] 🔐 Phát hiện popup 'XÁC MINH THAO TÁC'!")

        # Step 4a: read the question line (e.g. "Mật mã Pokeball: 17 - 16 = ?")
        question_text = page.get_by_text("Mật mã Pokeball:").inner_text().strip()
        log.info("[captcha] Question text: '%s'", question_text)

        # Step 4b: parse the math expression
        math_re = re.compile(
            r"(-?\d+)\s*([+\-*/x×÷])\s*(-?\d+)",
            re.UNICODE,
        )
        match = math_re.search(question_text)
        if not match:
            log.error("[captcha] Could not parse math expression from: '%s'", question_text)
            return False

        a  = int(match.group(1))
        op = match.group(2).strip()
        b  = int(match.group(3))
        log.info("[captcha] Parsed: %d %s %d", a, op, b)

        # Step 4c: calculate safely (NO eval)
        result = _safe_calc(a, op, b)
        if result is None:
            log.error("[captcha] Calculation failed – skipping captcha submission.")
            return False

        log.info("[captcha] Answer: %d", result)

        # Step 4d: fill the answer input via placeholder text
        page.get_by_placeholder("Nhập kết quả").fill(str(result))
        log.info("[captcha] Answer '%d' filled into input.", result)

        # Step 4e: click confirm button
        page.get_by_role("button", name="Xác nhận").click()
        log.info("[captcha] 'Xác nhận' button clicked.")

        # Step 4f: short human-like pause then signal success
        random_delay(1.0, 2.0)
        log.info("[captcha] ✅ Captcha solved successfully.")
        return True

    except PlaywrightTimeoutError as e:
        log.warning("[captcha] TimeoutError while solving captcha (dialog may have closed): %s", e)
        return False
    except Exception as e:
        log.error("[captcha] Unexpected error: %s", e)
        return False
