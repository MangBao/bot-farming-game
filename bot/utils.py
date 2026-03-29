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


def send_telegram_notification(pokemon_name: str, rank: str, hp: str) -> None:
    """
    Send a Telegram message when a high value Pokemon is caught.
    Safely ignores exceptions to prevent bot crash if network error occurs.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    text = f"🎉 **BẮT THÀNH CÔNG POKEMON XỊN!** 🎉\n\n🐉 **Tên:** {pokemon_name}\n⭐ **Rank:** {rank}\n❤️ **HP:** {hp}"
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            log.warning(f"[telegram] Failed to send message. HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log.warning(f"[telegram] Exception calling Telegram API: {e}")
