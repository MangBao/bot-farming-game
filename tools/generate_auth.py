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
            
            print("⌛ [5/6] Đang chờ điều hướng vào game... (Chỉnh timeout 60s để bạn kịp giải Captcha nếu có)")
            
            # Chờ đợi URL không còn chứa 'login' và trang web thực tế đã load
            # Ở đây tôi dùng wait_for_url với một function predicate hoặc timeout dài
            try:
                # Nếu trang yêu cầu Cloudflare, nó sẽ bị kẹt ở đây. 
                # Timeout 60s đủ dài để người dùng can thiệp click tay vào box Cloudflare nếu nó hiện ra.
                page.wait_for_url(lambda url: "login" not in url.lower() and GAME_HOST in url.lower(), timeout=60_000)
                
                # Check thêm sự tồn tại của một element trong game để chắc chắn (ví dụ thanh menu, hoặc avatar)
                # Dùng selector chung chung thường thấy trong game RPG
                page.wait_for_load_state("networkidle", timeout=15_000)
                
                print("✅ Đăng nhập thành công! Đã vào giao diện game.")
            except Exception:
                # Nếu timeout mà vẫn ở trang login, có thể là do login sai hoặc bị kẹt Captcha
                if "login" in page.url.lower():
                    print("❌ Lỗi: Không thể vào game sau 60 giây. Có thể bạn cần giải Captcha thủ công hoặc sai mật khẩu.")
                    print(f"URL hiện tại: {page.url}")
                    return
                else:
                    print(f"⚠️ Cảnh báo: URL hiện tại là {page.url}, tiếp tục lưu session...")

            print(f"💾 [6/6] Đang lưu phiên đăng nhập vào file: {auth_path}")
            context.storage_state(path=str(auth_path))
            
            print(f"✨ HOÀN TẤT! File '{auth_path}' đã sẵn sàng. Bạn có thể đóng trình duyệt.")
            time.sleep(2)

        except Exception as e:
            print(f"❌ Có lỗi nghiêm trọng: {e}")
            
        finally:
            browser.close()
            print("👋 Đã đóng trình duyệt.")

if __name__ == "__main__":
    generate_auth_automated()
