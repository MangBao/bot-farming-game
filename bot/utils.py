import io
import os
import json
import time
import random
import logging
import requests
import threading
from pathlib import Path
from PIL import Image

import config

log = logging.getLogger(__name__)

# Data storage for map-specific special Pokémon
SPECIAL_PKM_FILE = os.path.join(os.path.dirname(__file__), "data", "special_pokemon.json")

def load_special_pokemon():
    """Load the special Pokémon data with 'maps' structure."""
    if os.path.exists(SPECIAL_PKM_FILE):
        try:
            with open(SPECIAL_PKM_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Migration: If it's a flat dict (old format), wrap it in 'maps'
                if isinstance(data, dict) and "maps" not in data:
                    log.info("[data] Migrating old special_pokemon.json to new structure...")
                    data = {"maps": data}
                elif not isinstance(data, dict):
                    data = {"maps": {}}
                
                return data
        except Exception as e:
            log.error(f"[data] Error loading special Pokémon file: {e}")
    return {"maps": {}}

def save_special_pokemon(data):
    """Save the special Pokémon data to JSON."""
    try:
        os.makedirs(os.path.dirname(SPECIAL_PKM_FILE), exist_ok=True)
        with open(SPECIAL_PKM_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log.error(f"[data] Error saving special Pokémon file: {e}")


def random_sleep(min_s: float, max_s: float) -> None:
    """Sleep for a random duration in [min_s, max_s] to mimic human behaviour."""
    delay = random.uniform(min_s, max_s)
    log.debug("[sleep] %.2fs...", delay)
    time.sleep(delay)

def random_delay(
    min_sec: float = config.DELAY_MIN,
    max_sec: float = config.DELAY_MAX,
) -> None:
    """Legacy alias: Every significant UI interaction should be preceded by this call."""
    random_sleep(min_sec, max_sec)

def send_telegram_alert(message: str) -> None:
    """Send an emergency text-only alert via Telegram."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": f"⚠️ <b>CẢNH BÁO TỪ BOT:</b>\n\n{message}",
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=3)
    except Exception:
        pass


def is_special_variant(pokemon_name: str) -> bool:
    """Check if the Pokemon is a special variant (e.g., ESPEON (RAINBOW))."""
    return "(" in pokemon_name


BALL_IMAGE_URLS = {
    "PokeBall": f"https://{config.ASSETS_DOMAIN}/dovtqazow/image/upload/f_auto,q_auto:eco,dpr_auto,c_limit/v1770539411/pokemon/PokeBall_nn6fs0.png",
    "Great Ball": f"https://{config.ASSETS_DOMAIN}/dovtqazow/image/upload/f_auto,q_auto:eco,dpr_auto,c_limit/v1770539475/pokemon/GreatBall_qhe7x9.png",
    "Ultra Ball": f"https://{config.ASSETS_DOMAIN}/dovtqazow/image/upload/f_auto,q_auto:eco,dpr_auto,c_limit/v1770539621/pokemon/UltraBall_jdphwp.png",
    "MasterBall": f"https://{config.ASSETS_DOMAIN}/dovtqazow/image/upload/f_auto,q_auto:eco,dpr_auto,c_limit/v1770539731/pokemon/MasterBall_gxo0hk.png"
}

def send_telegram_notification(
    pokemon_name: str, 
    rank: str, 
    hp: str, 
    used_ball: str = "PokeBall", 
    image_url: str = None, 
    is_new_pokedex: bool = False,
    is_special_variant: bool = False,
    is_must_catch: bool = False
) -> None:
    """
    Send a compact Telegram message with a 500x250 banner background.
    Bypasses Telegram's auto-zooming by centering the Pokemon image on a fixed canvas.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    # 1. Prepare UI components
    BALL_EMOJIS = {"PokeBall": "🔴", "Great Ball": "🔵", "Ultra Ball": "🟡", "MasterBall": "🟣"}
    ball_emoji = BALL_EMOJIS.get(used_ball, "⚪")
    pokedex_badge = "🌟 <b>[ NEW POKEDEX ENTRY ]</b> 🌟\n" if is_new_pokedex else ""
    variant_badge = "🌈 <b>[ POKEMON ĐẶC BIỆT ]</b> 🌈\n" if is_special_variant else ""
    must_catch_badge = "🌟 <b>[ MỤC TIÊU ĐẶC BIỆT ]</b> 🌟\n" if is_must_catch else ""
    
    caption = (
        f"🎊 <b>BẮT THÀNH CÔNG POKEMON!</b> 🎊\n\n"
        f"{must_catch_badge}{pokedex_badge}{variant_badge}"
        f"{ball_emoji} <b>[ {used_ball} ] Tên:</b> {pokemon_name}\n"
        f"✨ <b>Rank:</b> {rank}\n"
        f"💖 <b>HP:</b> {hp}\n\n"
        f"🤖 <i>Target Auto Bot</i>"
    )

    # 2. Handle image processing
    if image_url and image_url.startswith("/"):
        image_url = f"{config.BASE_URL}{image_url}"

    success = False
    if image_url:
        try:
            # A. Download Pokemon image with Retry logic (Fake User-Agent bypass)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"{config.BASE_URL}/"
            }
            
            pkm_response = None
            for attempt in range(3):
                try:
                    pkm_response = requests.get(image_url, headers=headers, timeout=10)
                    if pkm_response.status_code == 200:
                        break
                except Exception:
                    time.sleep(1)
            
            if pkm_response and pkm_response.status_code == 200:
                pkm_img = Image.open(io.BytesIO(pkm_response.content)).convert("RGBA")
                
                # B. Create a Banner Canvas (500x250, Dark Mode friendly #2B3136)
                banner_width, banner_height = 500, 250
                bg = Image.new("RGBA", (banner_width, banner_height), (43, 49, 54, 255))
                
                # C. Center the Pokemon on the banner
                offset_x = (banner_width - pkm_img.width) // 2
                offset_y = (banner_height - pkm_img.height) // 2
                bg.paste(pkm_img, (offset_x, offset_y), pkm_img)
                
                # D. Export to Bytes
                output_bytes = io.BytesIO()
                bg.save(output_bytes, format="PNG")
                output_bytes.seek(0)

                # E. Send as Photo to Telegram (Increased timeout for reliable upload)
                url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto"
                data = {"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"}
                files = {"photo": ("pokemon_banner.png", output_bytes)}
                
                res = requests.post(url, data=data, files=files, timeout=15)
                if res.status_code == 200:
                    success = True
            else:
                log.warning(f"[telegram] Không thể tải ảnh PKM sau 3 lần thử (URL: {image_url})")
        except Exception as e:
            log.error(f"[telegram] Image Banner creation/upload failed: {e}")

    # 3. Fallback: sendMessage if image failed
    if not success:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=3)
        except Exception:
            pass

def send_telegram_reply(text: str):
    """Send a basic HTML-formatted text reply."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=3)
    except Exception:
        pass

def check_telegram_commands():
    """Poll Telegram getUpdates for remote control commands (/pause, /resume, /status)."""
    if not config.TELEGRAM_BOT_TOKEN:
        return
        
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"offset": config.BOT_STATE.get("last_update_id", 0) + 1, "timeout": 1}
    
    try:
        response = requests.get(url, params=params, timeout=3).json()
        if response.get("ok") and response["result"]:
            for update in response["result"]:
                config.BOT_STATE["last_update_id"] = update["update_id"]
                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()
                chat_id = str(msg.get("chat", {}).get("id", ""))
                
                # Security: Only process commands from the configured Chat ID
                if chat_id != str(config.TELEGRAM_CHAT_ID):
                    continue
                
                if text == "/pause":
                    config.BOT_STATE["is_paused"] = True
                    log.info("[remote] Bot paused via Telegram.")
                    send_telegram_reply("⏸️ <b>Đã tạm dừng Bot!</b> Nhắn /resume để chạy tiếp.")
                elif text == "/resume":
                    config.BOT_STATE["is_paused"] = False
                    log.info("[remote] Bot resumed via Telegram.")
                    send_telegram_reply("▶️ <b>Bot tiếp tục đi săn!</b>")
                elif text == "/status":
                    status_text = (
                        f"📊 <b>BÁO CÁO TÌNH HÌNH:</b>\n\n"
                        f"• <b>Trạng thái:</b> {'⏸️ Đang nghỉ' if config.BOT_STATE.get('is_paused') else '▶️ Đang săn'}\n"
                        f"• <b>Đã gặp:</b> {config.BOT_STATE['stats']['encounters']} con\n"
                        f"• <b>Đã bắt:</b> {config.BOT_STATE['stats']['caught']} con\n"
                        f"• <b>HP Sếp:</b> <code>{config.BOT_STATE['player_hp']}</code>\n\n"
                        f"🤖 <i>Target Remote Manager</i>"
                    )
                    send_telegram_reply(status_text)
                elif text == "/mapinfo":
                    event_maps = []
                    regular_maps = []
                    
                    for slug, info in config.maps_data.items():
                        # Lấy tên map từ file JSON, nếu không có thì format từ slug
                        map_name = ""
                        if isinstance(info, dict):
                            map_name = info.get("name", "")
                        
                        if not map_name:
                            map_name = slug.replace("-", " ").title()

                        # Format theo yêu cầu: 📍 [Tên Map]: `id_map`
                        # <code> giúp Telegram tự động copy khi chạm vào trên mobile
                        entry = f"📍 {map_name}: <code>{slug}</code>"
                        
                        if "event" in slug.lower():
                            event_maps.append(entry)
                        else:
                            regular_maps.append(entry)
                    
                    message = "🗺️ <b>DANH SÁCH BẢN ĐỒ KHẢ DỤNG</b> 🗺️\n\n"
                    
                    if event_maps:
                        message += "🔥 <b>KHU VỰC SỰ KIỆN:</b>\n" + "\n".join(event_maps) + "\n\n"
                    
                    if regular_maps:
                        message += "🌍 <b>BẢN ĐỒ THẾ GIỚI:</b>\n" + "\n".join(regular_maps) + "\n\n"
                    
                    message += "👉 <i>Dùng lệnh: /map [tên-map] để chuyển vùng!</i>"
                    send_telegram_reply(message)
                elif text.startswith("/map"):
                    parts = text.split(maxsplit=1)
                    if len(parts) >= 2:
                        region = parts[1].strip().lower()
                        if region.startswith("event-"):
                            slug = region
                        else:
                            slug = f"vung-{region}" if not region.startswith("vung-") else region
                        config.BOT_STATE["change_map_to"] = slug
                        send_telegram_reply(f"🔄 <b>Đã nhận lệnh!</b> Đang chuẩn bị chuyển bot sang <code>{region.capitalize()}</code>...")
                    else:
                        send_telegram_reply("⚠️ <b>Sai cú pháp!</b> Vui lòng nhập tên vùng. VD: <code>/map kanto</code>, <code>/map hoenn</code>")
                elif text == "/learn_map" or text == "/learn":
                    config.BOT_STATE["trigger_learn_map"] = True
                    send_telegram_reply("🧠 <b>Đang học lệnh!</b> Bot sẽ tiến hành quét danh sách Pokémon Đặc biệt tại vùng này ở vòng lặp tới...")
    except Exception:
        pass # Silence background network errors

def _telegram_polling_loop():
    """Vòng lặp chạy ngầm để kiểm tra lệnh Telegram mà không làm chậm Playwright."""
    while True:
        check_telegram_commands()
        # Nghỉ 1s giữa các lần gọi API để tránh bị Telegram chặn (Rate Limit)
        time.sleep(1)

def start_telegram_listener():
    """Khởi chạy luồng lắng nghe Telegram ngầm (Daemon Thread)."""
    listener_thread = threading.Thread(target=_telegram_polling_loop, daemon=True)
    listener_thread.start()
    log.info("[remote] Luồng lắng nghe Telegram đã được khởi chạy ngầm.")

