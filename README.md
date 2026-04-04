<div align="center">
  <br />
  <h1>🎮 Automated RPG Farming Bot</h1>
  <p><strong>Hệ thống tự động hóa Playwright siêu việt dành cho Web-based RPG (VNPet)</strong></p>

  <p>
    <img alt="Python Version" src="https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" />
    <img alt="Framework" src="https://img.shields.io/badge/Playwright-Automated-green?style=for-the-badge&logo=playwright&logoColor=white" />
    <img alt="License" src="https://img.shields.io/badge/License-MIT-purple?style=for-the-badge" />
    <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge" />
  </p>
  <p>
    <em>Quét hình ảnh, Giải Captcha, Tự động học mục tiêu & Đổ Loot về Telegram kèm Banner High-Fidelity.</em>
  </p>
</div>

<br />

## 📖 Giới thiệu

**Automated RPG Farming Bot** là hệ thống tự động hóa thao tác trình duyệt bằng **Headless Chrome (Playwright)**. Dự án được thiết kế chuyên biệt để thực hiện các nhiệm vụ phiêu lưu, bắt thú và cày tài nguyên 24/7. Bot sở hữu khả năng tự động học hỏi danh sách quái hiếm từ giao diện game, xử lý lỗi thông minh và cho phép điều khiển từ xa qua Telegram.

---

## ✨ Tính năng nổi bật

### 1. 🔍 Nhận diện & Auto Farm Thông Minh

- **Quét 24/7:** Tự động ấn nút "Tìm kiếm", xử lý các tình huống kẹt trang hoặc lỗi mạng.
- **Phân tách mục tiêu:** Tự động nhận diện Pokemon VIP (Rank S trở lên), Pokemon chưa có trong Pokedex (`NEW -`), và các biến dị đặc biệt (Shiny/Rainbow).
- **Hệ thống Map đa dạng:** Hỗ trợ đầy đủ các vùng đất từ Kanto đến Paldea và các **Khu vực Sự kiện** đặc biệt.

### 2. 🧠 Chế độ "Học Tập" Động (`/learn`)

- **Scrape mục tiêu hiếm:** Bot có khả năng quét giao diện "Pokemon Đặc Biệt" của map hiện tại và lưu vào cơ sở dữ liệu JSON (`special_pokemon.json`).
- **Ưu tiên bắt tuyệt đối:** Sau khi học, mọi Pokemon trong danh sách đặc biệt sẽ được ưu tiên bắt bằng mọi giá (Must Catch), bất kể Rank hay trạng thái Pokedex.

### 3. ⚔️ Trí Tuệ Chiến Đấu & Cày Xu

- **Thoát kẹt Softlock:** Cơ chế Flee mạnh mẽ, tự động `Hard Reset` (Tải lại trang) nếu bị kẹt UI hoặc Pokemon phe mình bị kiệt sức.
- **Smart Damage Tracking:** Tự động tính toán Damage để ép máu mục tiêu xuống mức tối thiểu (Safe HP Margin) trước khi ném bóng, tối ưu tỷ lệ bắt.
- **Tùy chỉnh hành vi:**
  - `AUTO_KILL_DUPLICATES`: Chọn giữa việc "Tiêu diệt" để cày xu hoặc "Bỏ chạy" để tiết kiệm thời gian khi gặp quái trùng.
  - `SPAM_ULTRA_BALL`: Tùy chỉnh việc sử dụng Ultra Ball cho quái thường để tối ưu tài nguyên.

### 4. 🧮 Auto Giải Math Captcha

- Tự động phát hiện và giải các phép tính (Cộng, Trừ, Nhân, Chia) ngay khi Pop-up kiểm tra xuất hiện, đảm bảo bot vận hành liên tục không gián đoạn.

### 5. 📱 Telegram Remote Control & Logging

- **Banner High-Fidelity:** Thông báo chiến lợi phẩm kèm ảnh banner 500x250 được render chuyên nghiệp (sử dụng Pillow).
- **Cơ chế Retry siêu cấp:** Tự động thử lại 3 lần nếu việc tải ảnh từ game bị lỗi, tăng timeout upload lên 15s để đảm bảo thông báo luôn được gửi đi.
- **Hệ thống lệnh điều khiển từ xa:**
  - `/status`: Kiểm tra tình trạng sức khỏe, số lượng quái đã gặp/bắt và HP hiện tại.
  - `/mapinfo`: Hiển thị danh sách các Vùng thường và Vùng sự kiện đang có.
  - `/map [slug]`: Ra lệnh cho bot tự động chuyển vùng đất ngay tức thì.
  - `/learn`: Lệnh cho bot tự quét và học danh sách Pokemon đặc biệt tại Map hiện tại.
  - `/pause` / `/resume`: Tạm dừng hoặc tiếp tục hành trình.

---

## 🚀 Cài đặt & Khởi chạy

### Bước 1. Môi trường Ảo (Virtual Environment)

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

### Bước 2. Cài đặt Thư Viện

```bash
pip install -r requirements.txt
playwright install chromium
```

### Bước 3. Biến Môi Trường (.env)

Tạo file `.env` từ `.env.example` và cấu hình:

```env
GAME_EMAIL=your_email@gmail.com
GAME_PASSWORD=your_password
GAME_TARGET_MAP="Vùng Johto"
GAME_HOST=xxx.coms

# Toggles hành vi
AUTO_KILL_DUPLICATES=False
SPAM_ULTRA_BALL=True

# Telegram API
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Bước 4. Chạy Bot

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
