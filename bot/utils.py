"""
utils.py – Shared utility helpers.

Contains:
    • random_delay()  – human-like sleep between UI interactions
"""

import time
import random
import logging
import requests

import config

log = logging.getLogger(__name__)


def random_delay(
    min_sec: float = config.DELAY_MIN,
    max_sec: float = config.DELAY_MAX,
) -> None:
    """
    Sleep for a random duration in [min_sec, max_sec] to mimic human behaviour.
    Every significant UI interaction should be preceded by this call.
    """
    delay = random.uniform(min_sec, max_sec)
    log.debug("[delay] Sleeping %.2fs...", delay)
    time.sleep(delay)


BALL_IMAGE_URLS = {
    "PokeBall": "https://cdn.vnpet.games/dovtqazow/image/upload/f_auto,q_auto:eco,dpr_auto,c_limit/v1770539411/pokemon/PokeBall_nn6fs0.png",
    "Great Ball": "https://cdn.vnpet.games/dovtqazow/image/upload/f_auto,q_auto:eco,dpr_auto,c_limit/v1770539475/pokemon/GreatBall_qhe7x9.png",
    "Ultra Ball": "https://cdn.vnpet.games/dovtqazow/image/upload/f_auto,q_auto:eco,dpr_auto,c_limit/v1770539621/pokemon/UltraBall_jdphwp.png",
    "MasterBall": "https://cdn.vnpet.games/dovtqazow/image/upload/f_auto,q_auto:eco,dpr_auto,c_limit/v1770539731/pokemon/MasterBall_gxo0hk.png"
}

def send_telegram_notification(pokemon_name: str, rank: str, hp: str, used_ball: str = "", image_url: str = None) -> None:
    """
    Send a Telegram message when a high value Pokemon is caught.
    Safely ignores exceptions to prevent bot crash if network error occurs.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    # Prepare ball label with hidden hyperlink if mapped
    ball_url = BALL_IMAGE_URLS.get(used_ball, "")
    ball_display = f'<a href="{ball_url}">[ {used_ball} ]</a>' if ball_url else f'[ {used_ball} ]'

    caption = (
        f"🎊 <b>BẮT THÀNH CÔNG POKEMON!</b> 🎊\n\n"
        f"{ball_display} <b>Tên:</b> {pokemon_name}\n"
        f"✨ <b>Rank:</b> {rank}\n"
        f"💖 <b>HP:</b> {hp}\n\n"
        f"🤖 <i>VNPet Auto Bot</i>"
    )
    
    # Decide which API endpoint to use based on image type
    try:
        if image_url:
            if ".gif" in image_url.lower() or ".mp4" in image_url.lower():
                url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendAnimation"
                payload = {
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "animation": image_url,
                    "caption": caption,
                    "parse_mode": "HTML"
                }
            else:
                url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto"
                payload = {
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "photo": image_url,
                    "caption": caption,
                    "parse_mode": "HTML"
                }
        else:
            url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": caption,
                "parse_mode": "HTML"
            }

        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            log.warning(f"[telegram] Failed to send message. HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log.warning(f"[telegram] Exception calling Telegram API: {e}")
