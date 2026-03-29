"""
utils.py – Shared utility helpers.

Contains:
    • random_delay()  – human-like sleep between UI interactions
"""

import io
import time
import random
import logging
import requests
import threading
from PIL import Image

import config

log = logging.getLogger(__name__)


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
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        log.warning(f"[telegram_alert] Failed to send alert: {e}")


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
    is_special_variant: bool = False
) -> None:
    """
    Send a Telegram message when a high value Pokemon is caught.
    Composites the Pokemon image with the used Ball icon.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    # 1. Prepare UI components
    BALL_EMOJIS = {"PokeBall": "🔴", "Great Ball": "🔵", "Ultra Ball": "🟡", "MasterBall": "🟣"}
    ball_emoji = BALL_EMOJIS.get(used_ball, "⚪")
    pokedex_badge = "🌟 <b>[ NEW POKEDEX ENTRY ]</b> 🌟\n" if is_new_pokedex else ""
    variant_badge = "🌈 <b>[ POKEMON ĐẶC BIỆT ]</b> 🌈\n" if is_special_variant else ""
    
    caption = (
        f"🎊 <b>BẮT THÀNH CÔNG POKEMON!</b> 🎊\n\n"
        f"{pokedex_badge}{variant_badge}"
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
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"{config.BASE_URL}/"
            }
            
            # A. Download Pokemon image
            pkm_response = requests.get(image_url, headers=headers, timeout=10)
            if pkm_response.status_code == 200:
                pkm_img = Image.open(io.BytesIO(pkm_response.content)).convert("RGBA")
                
                # B. Download and Overlay Ball icon (if applicable)
                ball_url = BALL_IMAGE_URLS.get(used_ball)
                if ball_url:
                    try:
                        ball_res = requests.get(ball_url, headers=headers, timeout=5)
                        if ball_res.status_code == 200:
                            ball_img = Image.open(io.BytesIO(ball_res.content)).convert("RGBA")
                            
                            # C. Composite: Resize ball and paste onto PKM image
                            ball_icon_size = (int(pkm_img.width * 0.2), int(pkm_img.width * 0.2)) # Dynamic size (20% of width)
                            # Or lock to 50x50 as requested
                            ball_icon_size = (50, 50)
                            ball_img.thumbnail(ball_icon_size, Image.Resampling.LANCZOS)
                            
                            # Bottom-right corner with 10px margin
                            offset = (
                                pkm_img.width - ball_img.width - 10,
                                pkm_img.height - ball_img.height - 10
                            )
                            pkm_img.paste(ball_img, offset, ball_img)
                    except Exception as e:
                        log.warning(f"[telegram] Ball overlay failed, sending PKM image only: {e}")

                # D. Convert composite to Bytes
                output_bytes = io.BytesIO()
                pkm_img.save(output_bytes, format="PNG")
                output_bytes.seek(0)

                # E. Send to Telegram
                is_anim = ".gif" in image_url.lower() or ".mp4" in image_url.lower()
                endpoint = "/sendAnimation" if is_anim else "/sendPhoto"
                file_field = "animation" if is_anim else "photo"
                
                url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}{endpoint}"
                data = {"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"}
                files = {file_field: ("composite.png", output_bytes)}
                
                res = requests.post(url, data=data, files=files, timeout=15)
                if res.status_code == 200:
                    success = True
                else:
                    log.warning(f"[telegram] Upload rejected (HTTP {res.status_code}): {res.text}")
            else:
                log.warning(f"[telegram] Could not download PKM image (HTTP {pkm_response.status_code})")
        except Exception as e:
            log.warning(f"[telegram] Image compositing failed: {e}")

    # 3. Fallback: Plaintext message
    if not success:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            log.error(f"[telegram] Fatal notification failure: {e}")

def send_telegram_reply(text: str):
    """Send a basic HTML-formatted text reply."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=5)
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
                    map_list_text = (
                        "🗺️ <b>DANH SÁCH BẢN ĐỒ HIỆN CÓ:</b>\n\n"
                        "🔹 <code>/map kanto</code> - Vùng Kanto\n"
                        "🔹 <code>/map johto</code> - Vùng Johto\n"
                        "🔹 <code>/map hoenn</code> - Vùng Hoenn\n"
                        "🔹 <code>/map sinnoh</code> - Vùng Sinnoh\n"
                        "🔹 <code>/map unova</code> - Vùng Unova\n"
                        "🔹 <code>/map kalos</code> - Vùng Kalos\n"
                        "🔹 <code>/map alola</code> - Vùng Alola\n"
                        "🔹 <code>/map galar</code> - Vùng Galar\n"
                        "🔹 <code>/map paldea</code> - Vùng Paldea\n\n"
                        "💡 <i>Mẹo: Gõ đúng cú pháp trên để lệnh cho bot chuyển map ngay lập tức!</i>"
                    )
                    send_telegram_reply(map_list_text)
                elif text.startswith("/map"):
                    parts = text.split(maxsplit=1)
                    if len(parts) >= 2:
                        region = parts[1].strip().lower()
                        # Auto-prefix 'vung-' if missing for slug consistency
                        slug = f"vung-{region}" if not region.startswith("vung-") else region
                        config.BOT_STATE["change_map_to"] = slug
                        send_telegram_reply(f"🔄 <b>Đã nhận lệnh!</b> Đang chuẩn bị chuyển bot sang <code>{region.capitalize()}</code>...")
                    else:
                        send_telegram_reply("⚠️ <b>Sai cú pháp!</b> Vui lòng nhập tên vùng. VD: <code>/map kanto</code>, <code>/map hoenn</code>")
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

