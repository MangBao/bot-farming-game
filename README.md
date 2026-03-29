<div align="center">
  <br />
  <h1>🎮 Automated RPG Farming Bot</h1>
  <p><strong>Hệ thống tự động hóa Playwright siêu việt dành cho Web-based RPG</strong></p>

  <p>
    <img alt="Python Version" src="https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" />
    <img alt="Framework" src="https://img.shields.io/badge/Playwright-Automated-green?style=for-the-badge&logo=playwright&logoColor=white" />
    <img alt="License" src="https://img.shields.io/badge/License-MIT-purple?style=for-the-badge" />
    <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge" />
  </p>
  <p>
    <em>Quét hình ảnh, Giải Captcha, Tính toán Damage & Đổ Loot về Telegram theo thời gian thực.</em>
  </p>
</div>

<br />

## 📖 Giới thiệu

**Automated RPG Farming Bot** là hệ thống tự động hóa thao tác trình duyệt bằng **Headless Chrome (Playwright)**. Dự án sinh ra để thay thế con người thực hiện các nhiệm vụ phiêu lưu, bắt thú, cày cuốc tài nguyên lặp đi lặp lại hàng giờ liền trong môi trường Web-based RPG. Điểm mạnh của bot nằm ở kiến trúc module hóa gọn gàng, linh hoạt tùy biến và khả năng xử lý tình huống cực kỳ thông minh.

---

## ✨ Tính năng nổi bật

### 1. 🔍 Nhận diện DOM & Auto Farm 24/7
- Quét liên tục bản đồ, tự động ấn nút "Tìm kiếm".
- Bypass màn hình tải trang với các khối `try/except` và timeout linh động.

### 2. 🧮 Auto Giải Math Captcha (Anti-Auto Click)
- Quét toàn dải RegExp khi Pop-up "*Kiểm tra thao tác*" xuất hiện.
- Tự động bóc tách phép tính (Cộng, Trừ, Nhân, Chia), tính toán kết quả và điền số ẩn danh như người thật chỉ trong chớp mắt.

### 3. ⚔️ Dynamic Damage Tracking & Máu An Toàn
- **Chốt chặn an toàn (Safe HP Margin):** Bot tự động chạy ngay thoát hiểm nếu máu team mình rơi xuống dưới **15%**.
- **Đọc log combat:** Bóc bóc sát thương tạo thành biến số động để ước lượng đòn đánh kết liễu (`Max Hit + Buffer`).
- Liên tục bào máu mục tiêu mà **không bao giờ đánh chết chúng**, tối đa tỉ lệ thu phục.

### 4. 🎯 Bộ Lọc Bắt Đồ VIP (Smart Rarity Filter)
- Né rác: Lọc độ hiếm mục tiêu để bỏ chạy hoặc tiếp tục, tối ưu tỷ lệ ném bóng.
- **Pokedex Override:** Tự bắt mọi quái vật gắn tag "*Chưa có trong Pokedex*" bất kể cấp độ.
- Hệ thống Fallback PokéBall chọn thông minh bóng tối ưu chi phí tỉ lệ.

### 5. 📱 Telegram Loot Logger
- Thông báo chiến lợi phẩm cao cấp đập thẳng vào điện thoại qua Telegram API.
- Báo cáo số HP, Rank và trạng thái bắt gọn gàng, kèm biểu cảm.

---

## 🚀 Cài đặt & Khởi chạy

> Đảm bảo máy tính của bạn đã cài đặt **Python 3.10+**.

### Bước 1. Môi trường Ảo (Virtual Environment)
Tài nguyên không ảnh hưởng tới các script khác của hệ thống:
```bash
python -m venv venv

# Kích hoạt trên Windows
venv\Scripts\activate
# Kích hoạt trên macOS/Linux
source venv/bin/activate
```

### Bước 2. Cài đặt Thư Viện
```bash
pip install -r requirements.txt
pip install playwright requests python-dotenv

# Tải lõi trình duyệt Chrome headless
playwright install chromium
```

### Bước 3. Biến Môi Trường (.env)
Sao chép cấu hình mẫu và nhập chính xác tài khoản bằng bất kỳ định dạng Text Code Editor nào bạn có, chẳng hạn VSCode hoặc Notepad++:
```bash
cp .env.example .env
```

<details>
<summary>👀 Giao diện mẫu file .env (Bấm để xem)</summary>

```env
GAME_EMAIL=your_email_here
GAME_PASSWORD=your_password_here
GAME_HOST=target-website.com
GAME_TARGET_MAP="Vùng Johto"
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```
</details>

### Bước 4. Thử Nghiệm

Mở Terminal và trỏ lệnh về tệp thực thi chính:
```bash
python bot/main.py
```

---

## 🔒 Lưu ý bảo mật nghiêm ngặt

> [!WARNING]
> Tệp `.env` chứa những chứng chỉ vô cùng nhạy cảm (Tài khoản, Mật khẩu, API Token kết nối Server Telegram). 
> **TUYỆT ĐỐI KHÔNG COMMMIT ĐÈ** file này lên một Repositories Public trên nền tảng GitHub. Hãy luôn giữ tệp `.gitignore` trong tình trạng khóa file `.env`. Nếu phát hiện Token bị lọt ra ngoài, hãy Generate mã BOT mới tại [BotFather](https://t.me/BotFather) ngay lập tức!

---
<div align="center">
  <sub>Cất cánh tự do với thế giới tự động hóa! Xây dựng bằng 💖 và Playwright.</sub>
</div>