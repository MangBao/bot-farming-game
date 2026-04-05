"""
auth.py – Login and initial navigation.

Contains:
    • login_and_navigate(page)  – fill credentials, submit, go to Johto map
"""

import logging
import sys
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

import config
from utils import random_delay, random_sleep, send_telegram_reply

log = logging.getLogger(__name__)


def auto_login(page: Page) -> bool:
    """Tự động đăng nhập nếu đang ở màn hình login."""
    try:
        # Check if login form is visible
        email_input = page.locator("input[type='email'], input[name='email'], input[type='password']").first
        if not email_input.is_visible(timeout=3_000):
            return True
            
        log.info("[auto_login] Phát hiện bị văng ra trang đăng nhập, đang tiến hành đăng nhập lại...")
        
        email_field = page.locator("input[type='email'], input[name='email']").first
        if email_field.is_visible():
            email_field.fill(config.EMAIL)
            
        password_input = page.locator("input[type='password']").first
        if password_input.is_visible():
            password_input.fill(config.PASSWORD)
            
        login_btn = page.get_by_role("button", name="Đăng Nhập")
        if not login_btn.is_visible():
            login_btn = page.locator("button[type='submit'], input[type='submit']").first
        
        login_btn.click()
        # Chờ UI ổn định thay vì networkidle
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000) 
        
        if email_field.is_visible(timeout=3000):
            log.error("[auto_login] Vẫn còn ở trang đăng nhập. Thất bại.")
            return False
            
        log.info(f"[auto_login] Đăng nhập thành công, chuyển lẹ đến {config.MAP_URL}")
        page.goto(config.MAP_URL, wait_until="domcontentloaded")
        
        # Kiểm tra nút 'Tải lại trang' nếu game bị lỗi
        if page.get_by_role("button", name="Tải lại trang").is_visible(timeout=2000) or "Đã xảy ra lỗi" in page.content():
            log.warning("[auth] Phát hiện lỗi trang. Đang thực hiện reload...")
            page.reload()
            page.wait_for_load_state("domcontentloaded")

        try:
            page.get_by_role("button", name="Tìm kiếm").wait_for(state="visible", timeout=60_000)
        except PlaywrightTimeoutError as e:
            log.error("[auth] Timeout khi đợi nút Tìm kiếm tại map. Đang chụp ảnh màn hình debug...")
            page.screenshot(path="error_map_screen.png", full_page=True)
            raise e
        
        return True
    except PlaywrightTimeoutError:
        log.error("[auto_login] Lỗi Timeout khi auto-login.")
        return False
    except Exception as e:
        log.error(f"[auto_login] Lỗi khi auto-login: {e}")
        return False

def check_map_locked(page: Page) -> bool:
    """Check if the current map is locked by looking for requirement text."""
    log.info("[auth] Đang kiểm tra trạng thái map...")
    page.wait_for_timeout(2000) # Quick settle time
    
    # Common lock indicators: 'Yêu cầu tìm kiếm:', 'Yêu cầu cấp:', 'Cần thêm'
    lock_selectors = [
        "text='Yêu cầu tìm kiếm:'",
        "text='Yêu cầu cấp:'",
        "text='Cần thêm'",
        "text='đã bị khóa'"
    ]
    
    is_locked = False
    for selector in lock_selectors:
        try:
            if page.locator(selector).is_visible(timeout=1000):
                is_locked = True
                break
        except Exception:
            continue
            
    if is_locked:
        error_msg = f"⛔ MAP BỊ KHÓA! Bot không thể cày ở {config.TARGET_MAP} vì chưa đủ điều kiện."
        log.error(error_msg)
        send_telegram_reply(f"⚠️ <b>BÁO ĐỘNG TỪ AUTO BOT</b> ⚠️\n\n{error_msg}\n\n<i>Hãy dùng lệnh /map để chuyển vùng hoặc đổi map trong .env!</i>")
        return True
    
    return False

def login_and_navigate(page: Page, skip_login_fields: bool = False) -> None:
    """
    Navigate to the login page, fill credentials, submit, then go to the Johto map.
    Raises PlaywrightTimeoutError if any step times out.
    """
    
    # ── Handle Existing Session ──────────────────────────────────────────────
    if skip_login_fields:
        log.info("[auth] ✨ Đang bỏ qua bước đăng nhập... Đang nạp session.")
        log.info("[auth] 🚜 Đang chuyển đến map ngay lập tức: %s", config.MAP_URL)
        page.goto(config.MAP_URL, wait_until="domcontentloaded")
        
        # Kiểm tra nút 'Tải lại trang' nếu game bị lỗi
        if page.get_by_role("button", name="Tải lại trang").is_visible(timeout=3000) or "Đã xảy ra lỗi" in page.content():
            log.warning("[auth] Phát hiện lỗi trang hoặc nút Tải lại. Đang thực hiện reload...")
            page.reload()
            page.wait_for_load_state("domcontentloaded")

        # Thay thế networkidle bằng việc đợi nút 'Tìm kiếm' xuất hiện
        try:
            page.get_by_role("button", name="Tìm kiếm").wait_for(state="visible", timeout=60_000)
        except PlaywrightTimeoutError as e:
            log.error("[auth] [Session] Timeout khi đợi nút Tìm kiếm. Đang chụp ảnh màn hình debug...")
            page.screenshot(path="error_map_screen.png", full_page=True)
            raise e
        
        # Kiểm tra xem có bị đá ra trang login không
        current_url = page.url.lower()
        if "login" in current_url:
            log.error("[auth] ⚠️ Lỗi SESSION HẾT HẠN! auth.json không còn hiệu lực.")
            log.error("[auth] Hãy chạy tools/generate_auth.py ở máy local để tạo lại file mới.")
            sys.exit(1)
            
        log.info("[auth] Đăng nhập bằng session thành công!")
        return

    # ── Open login page ──────────────────────────────────────────────────────
    log.info("[auth] Navigating to login page: %s", config.LOGIN_URL)
    page.goto(config.LOGIN_URL, wait_until="domcontentloaded")
    random_delay()

    try:
        # ── Fill email ───────────────────────────────────────────────────────────
        log.info("[auth] Filling email...")
        email_input = page.get_by_label("Email", exact=False)
        if not email_input.is_visible(timeout=4_000):
            email_input = page.locator(
                "input[type='email'], input[name='email'], input[name='username']"
            ).first
        
        # This is where the timeout usually happens
        email_input.wait_for(state="visible", timeout=15_000)
        email_input.fill(config.EMAIL)
        random_delay()

        # ── Fill password ─────────────────────────────────────────────────────────
        log.info("[auth] Filling password...")
        password_input = page.get_by_label("Password", exact=False)
        if not password_input.is_visible(timeout=4_000):
            password_input = page.locator("input[type='password']").first
        password_input.wait_for(state="visible", timeout=10_000)
        password_input.fill(config.PASSWORD)
        random_delay()

        # ── Click login button ───────────────────────────────────────────────────
        log.info("[auth] Clicking 'Đăng Nhập'...")
        login_button = page.get_by_role("button", name="Đăng Nhập")
        login_button.wait_for(state="visible", timeout=10_000)
        login_button.click()
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        page.wait_for_timeout(2000)
        random_delay()
    except Exception as e:
        log.error(f"[auth] Lỗi trong quá trình đăng nhập: {e}")
        log.info("[auth] Đang chụp ảnh màn hình lỗi: error_login_screen.png")
        page.screenshot(path="error_login_screen.png")
        raise e

    current_url = page.url
    if "login" in current_url.lower():
        log.warning("[auth] Still on login page – credentials may be wrong.")
    else:
        log.info("[auth] Login successful! URL: %s", current_url)

    # ── Navigate to map ──────────────────────────────────────────────────────
    log.info("[auth] Navigating to map: %s", config.MAP_URL)
    page.goto(config.MAP_URL, wait_until="domcontentloaded")

    # Kiểm tra nút 'Tải lại trang' nếu game bị lỗi
    if page.get_by_role("button", name="Tải lại trang").is_visible(timeout=2000) or "Đã xảy ra lỗi" in page.content():
        log.warning("[auth] Phát hiện lỗi trang. Đang thực hiện reload...")
        page.reload()
        page.wait_for_load_state("domcontentloaded")

    # Đợi nút Tìm kiếm để đảm bảo đã vào game thực sự
    try:
        page.get_by_role("button", name="Tìm kiếm").wait_for(state="visible", timeout=60_000)
    except PlaywrightTimeoutError as e:
        log.error("[auth] [Login] Timeout khi đợi nút Tìm kiếm. Đang chụp ảnh màn hình debug...")
        page.screenshot(path="error_map_screen.png", full_page=True)
        raise e
    
    # ── Map Lock Security Check ──────────────────────────────────────────────
    if check_map_locked(page):
        log.info("[auth] Map is locked. Shutting down bot to prevent errors.")
        sys.exit(1)
        
    log.info("[auth] Arrived at map successfully.")
    random_delay()
