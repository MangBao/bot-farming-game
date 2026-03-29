"""
discovery_loop.py – DOM trinh sát cho Target Games (Loop cho đến khi gặp Pokemon).

Mục đích:
    1. Login và vào map Johto.
    2. Click 'Tìm kiếm' liên tục (có delay) cho đến khi bắt gặp Pokemon.
    3. Dump toàn bộ HTML -> encounter_dump.html
    4. Chụp ảnh màn hình -> encounter_result.png
"""

import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("discovery")

load_dotenv()
EMAIL = os.environ.get("GAME_EMAIL")
PASSWORD = os.environ.get("GAME_PASSWORD")

def run_discovery() -> None:
    with sync_playwright() as pw:
        # Tắt headless để dễ quan sát (có thể bật lại nếu quá chậm)
        browser = pw.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()

        log.info("Logging in...")
        page.goto("https://target.com/login", wait_until="domcontentloaded")
        page.locator("input[type='email']").first.fill(EMAIL)
        page.locator("input[type='password']").first.fill(PASSWORD)
        page.get_by_role("button", name="Đăng Nhập").click()
        page.wait_for_load_state("networkidle")

        log.info("Going to map...")
        page.goto("https://target.com/map/vung-johto", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        search_btn = page.get_by_role("button", name="Tìm kiếm")
        
        loop = 0
        while loop < 30:
            loop += 1
            log.info(f"--- Attempt {loop} ---")
            try:
                search_btn.wait_for(state="visible", timeout=5000)
                search_btn.click()
            except Exception as e:
                log.error(f"Cannot click search: {e}")
            
            # Đợi một chút để UI cập nhật
            time.sleep(1.5)
            
            # Check captcha here? Just basic check. Wait for networkidle
            try:
                page.wait_for_function(
                    "() => document.body.innerText.includes('Không tìm thấy') || document.body.innerText.includes('HP') || document.body.innerText.includes('Chiến đấu')",
                    timeout=8000
                )
            except PlaywrightTimeoutError:
                log.warning("Timeout waiting for result (maybe captcha occurred?)")
            
            body = page.locator("body").inner_text()
            
            if "Không tìm thấy" in body:
                log.info("Không có Pokemon, thử lại...")
                time.sleep(2)
                continue
                
            if "Chiến đấu" in body or "Bỏ chạy" in body or "HP" in body:
                log.info("Bingo! Đã bắt gặp Pokemon!")
                time.sleep(2)  # Wait for animations
                
                # Take screenshot & dump
                html_content = page.content()
                
                os.makedirs("../debug_logs", exist_ok=True)
                with open("../debug_logs/encounter_dump.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                page.screenshot(path="../debug_logs/encounter_result.png", full_page=True)
                log.info("Saved encounter_dump.html and encounter_result.png to debug_logs/")
                return

        log.warning("Không tìm thấy Pokemon sau 30 lần thử.")
        
if __name__ == "__main__":
    run_discovery()
