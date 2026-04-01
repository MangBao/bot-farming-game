"""
config.py – Centralized configuration for the Target bot.

Contains:
    • Logging setup
    • Credential loading from .env
    • URL constants
    • All tuning constants and selector tuples
"""

import os
import logging
import sys
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging – configured once here; every module uses logging.getLogger(__name__)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ---------------------------------------------------------------------------
# Credentials  –  loaded from .env, fallback to placeholder
# ---------------------------------------------------------------------------
from pathlib import Path
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

EMAIL    = os.environ.get("GAME_EMAIL",    "YOUR_EMAIL")
PASSWORD = os.environ.get("GAME_PASSWORD", "YOUR_PASSWORD")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# Host and URLs - Derived from a single GAME_HOST for simplicity
# ---------------------------------------------------------------------------
import json

GAME_HOST = os.environ.get("GAME_HOST", "example.com").strip('"\' ')
BASE_URL = f"https://{GAME_HOST}"
LOGIN_URL = f"{BASE_URL}/login"
API_BASE_URL = f"{BASE_URL}/api"
ASSETS_DOMAIN = f"cdn.{GAME_HOST}"

# ---------------------------------------------------------------------------
# Map configuration - dynamically resolved from maps.json or raw slug
# ---------------------------------------------------------------------------
TARGET_MAP = os.environ.get("GAME_TARGET_MAP", "Vùng Johto").strip('"\' ')
maps_json_path = Path(__file__).parent / "maps.json"

try:
    with open(maps_json_path, encoding='utf-8') as f:
        maps_data = json.load(f)
except FileNotFoundError:
    maps_data = {}

# Use map from JSON if found, otherwise treat as raw relative URL slug
if TARGET_MAP in maps_data:
    map_info = maps_data[TARGET_MAP]
    rel_url = map_info.get("url")
    
    # If the JSON doesn't have an URL (e.g. locked map), generate it from the key
    if not rel_url:
        slug = TARGET_MAP.replace(" ", "-").lower()
        rel_url = f"/map/{slug}"
        
    MAP_URL = f"{BASE_URL}{rel_url}"
else:
    # Allow raw slugs like 'vung-sinnoh' directly from .env
    slug = TARGET_MAP.replace(" ", "-").lower()
    if not slug.startswith("/map/"):
        slug = f"/map/{slug}"
    MAP_URL = f"{BASE_URL}{slug}"
    log.info(f"[config] Using custom map URL: {MAP_URL}")


# ---------------------------------------------------------------------------
# Bot tuning constants
# ---------------------------------------------------------------------------

# Ranks always worth catching – VIP tier (S and above)
ALWAYS_CATCH_RANKS: set[str] = {"S", "SS", "SSS", "SSS+", "R", "SR", "SSR", "UR", "UR+", "LR", "MR", "GR", "GOD"}

# High value ranks to notify via Telegram
HIGH_VALUE_RANKS: set[str] = {"S", "SS", "SSS", "SSS+", "R", "SR", "SSR", "UR", "UR+", "LR", "MR", "GR", "GOD"}

# HP threshold below which we attempt a capture (30 %)
CAPTURE_HP_THRESHOLD: float = 0.30

# Safety cap: maximum attack rounds before forcing a capture attempt
MAX_ATTACK_ROUNDS: int = 30

# Human-like delay range (seconds)
DELAY_MIN: float = 0.5
DELAY_MAX: float = 1.2

# Delay after a failed scan before retrying (seconds)
RETRY_DELAY_MIN: float = 1.0
RETRY_DELAY_MAX: float = 2.0

# How many consecutive errors before attempting a full re-login
MAX_ERRORS_BEFORE_RELOGIN: int = 3

# Known rank tokens ordered rarest → most common (for regex detection)
RANK_TOKENS: tuple[str, ...] = ("GOD", "GR", "MR", "LR", "UR+", "UR", "SSR", "SR", "R", "SSS+", "SSS", "SS", "S", "A", "B", "C", "D")

# Bật True để ưu tiên Ultra Ball cho mọi quái từ Rank A trở xuống. False để dùng Great Ball cho quái cỏ.
SPAM_ULTRA_BALL = os.environ.get("SPAM_ULTRA_BALL", "True").upper() == "TRUE"

# True: Đánh đến chết để cày xu. False: Bỏ chạy ngay lập tức để tiết kiệm thời gian.
AUTO_KILL_DUPLICATES = os.environ.get("AUTO_KILL_DUPLICATES", "False").upper() == "TRUE"

# Danh sách Pokemon đặc biệt - Gặp là bắt bằng mọi giá (Đã chuyển sang JSON động qua lệnh /learn)

# ---------------------------------------------------------------------------
# Captcha selectors
# ---------------------------------------------------------------------------

# Dialog container selectors – waterfall from most-specific to generic.
DIALOG_SELECTORS: tuple[str, ...] = (
    "[class*=captcha]",
    "[class*=math-dialog]",
    "[class*=verify]",
    "[role='dialog']",
    ".modal",
    "[class*=popup]",
)

# Question text selectors inside the dialog
QUESTION_SELECTORS: tuple[str, ...] = (
    "[class*=captcha] p",
    "[class*=captcha] span",
    "[class*=captcha] h3",
    "[class*=captcha] h2",
    "[role='dialog'] p",
    "[role='dialog'] span",
    ".modal p",
)
# ---------------------------------------------------------------------------
# Bot Global State (Runtime Statistics & Remote Control)
# ---------------------------------------------------------------------------
BOT_STATE = {
    "is_paused": False,
    "stats": {"encounters": 0, "caught": 0},
    "last_update_id": 0,
    "player_hp": "Unknown"
}
