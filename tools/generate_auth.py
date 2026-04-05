import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load các biến môi trường từ file .env
BASE_DIR = Path(__file__).parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

EMAIL = os.getenv("GAME_EMAIL")
PASSWORD = os.getenv("GAME_PASSWORD")
GAME_HOST = os.getenv("GAME_HOST")
LOGIN_URL = f"https://{GAME_HOST}/login" if GAME_HOST else ""

def generate_auth_automated():
    if not EMAIL or not PASSWORD or not GAME_HOST:
        print("❌ Lỗi: GAME_EMAIL, GAME_PASSWORD hoặc GAME_HOST không tìm thấy trong file .env")
        return

    auth_path = BASE_DIR / "auth.json"
    print(f"🚀 [1/6] Đang khởi chạy trình duyệt (Headless=False)... Đang chuẩn bị tạo: {auth_path}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        
        # Sử dụng User-Agent giống trình duyệt thật
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"🔗 [2/6] Đang mở trang đăng nhập: {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        
        # Đợi các ô input xuất hiện
        try:
            print("⌨️ [3/6] Đang điền tài khoản và mật khẩu...")
            
            # Selector linh hoạt cho ô Email/Password
            email_input = page.locator("input[type='email'], input[name='email'], input[name='username']").first
            email_input.wait_for(state="visible", timeout=10_000)
            email_input.fill(EMAIL)
            
            password_input = page.locator("input[type='password']").first
            password_input.wait_for(state="visible", timeout=10_000)
            password_input.fill(PASSWORD)
            
            time.sleep(1) # Nghỉ nhẹ cho giống người dùng
            
            print("🔘 [4/6] Đang nhấn nút 'Đăng Nhập'...")
            login_btn = page.get_by_role("button", name="Đăng Nhập")
            if not login_btn.is_visible():
                login_btn = page.locator("button[type='submit'], input[type='submit']").first
            
            login_btn.click()
            
            # ⌛ [5/6] Đợi một chút rồi ép trình duyệt vào thẳng Map (Force Goto)
            time.sleep(5) 
            
            # Tính toán URL Map để force truy cập
            TARGET_SLUG = os.getenv("GAME_TARGET_MAP", "vung-johto").strip().lower().replace(" ", "-")
            if not TARGET_SLUG.startswith("/map/"):
                TARGET_SLUG = f"/map/{TARGET_SLUG}"
            MAP_FORCE_URL = f"https://{GAME_HOST}{TARGET_SLUG}"
            
            print(f"🚀 Đang ép trình duyệt truy cập Map: {MAP_FORCE_URL}")
            
            authenticated = False
            for attempt in range(1, 4):
                print(f"🔄 Thử lần {attempt}/3 để xác nhận trạng thái game...")
                try:
                    page.goto(MAP_FORCE_URL, wait_until="domcontentloaded", timeout=40_000)
                    
                    # ⌛ [D] Nghỉ 5 giây đợi game render (Yêu cầu của USER)
                    print("⌛ Đang nghỉ 5 giây đợi Javascript render toàn bộ UI...")
                    page.wait_for_timeout(5000)

                    # Kiểm tra xem có màn hình lỗi trắng hoặc nút 'Tải lại trang' không
                    if "Đã xảy ra lỗi" in page.content() or page.get_by_role("button", name="Tải lại trang").is_visible(timeout=2000):
                        print("⚠️ Phát hiện màn hình lỗi/loading. Đang thực thực hiện reload...")
                        page.reload()
                        page.wait_for_timeout(3000)

                    # Kiểm tra dấu hiệu thực tế của game (Mở rộng theo yêu cầu của USER)
                    found = False
                    
                    # A. Kiểm tra Text
                    text_indicators = ["CHI TIẾT BẢN ĐỒ", "THÔNG TIN KHU VỰC", "Tìm kiếm", "Túi đồ", "Hồ sơ"]
                    # B. Kiểm tra Link chính xác
                    link_indicators = ["[ Sự Kiện ]", "[ Cửa Hàng ]"]
                    
                    for text in text_indicators:
                        if page.get_by_text(text).first.is_visible(timeout=2000):
                            print(f"✅ Tìm thấy dấu hiệu Text: {text}")
                            found = True
                            break
                    
                    if not found:
                        for link in link_indicators:
                            if page.get_by_role("link", name=link).first.is_visible(timeout=2000):
                                print(f"✅ Tìm thấy dấu hiệu Link: {link}")
                                found = True
                                break
                    
                    if not found:
                        # C. Kiểm tra selector links chuyển map
                        if page.locator("a[href*='/map/']").first.is_visible(timeout=2000):
                            print("✅ Tìm thấy dấu hiệu: Các liên kết chuyển bản đồ")
                            found = True
                    
                    if found:
                        print("✨ XÁC NHẬN: Đã vào giao diện game thành công!")
                        authenticated = True
                        break
                    else:
                        print(f"⌛ Vẫn chưa thấy giao diện game (Lần {attempt})...")
                        # Debug: In 1000 ký tự đầu của trang để biết bot đang ở đâu
                        page_text = page.locator("body").inner_text().strip()
                        print(f"🔍 Nội dung trang thu gọn: {page_text[:300]}...")
                        time.sleep(2)
                except Exception as e:
                    print(f"⚠️ Lỗi khi truy cập (Lần {attempt}): {e}")

            if not authenticated:
                print("❌ Đăng nhập thất bại: Không thể vào được giao diện game sau 3 lần thử.")
                sys.exit(1)

            print(f"💾 [6/6] Đang lưu phiên đăng nhập vào file: {auth_path}")
            context.storage_state(path=str(auth_path))
            print(f"✨ HOÀN TẤT! File '{auth_path}' đã sẵn sàng.")
            time.sleep(1)
            sys.exit(0) # Thành công

        except Exception as e:
            print(f"❌ Có lỗi nghiêm trọng: {e}")
            
        finally:
            browser.close()
            print("👋 Đã đóng trình duyệt.")

if __name__ == "__main__":
    generate_auth_automated()
