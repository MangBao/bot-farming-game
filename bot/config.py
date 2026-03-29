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
# URLs
# ---------------------------------------------------------------------------
import json

BASE_URL = os.environ.get("GAME_BASE_URL", "https://target.com")
LOGIN_URL = os.environ.get("GAME_LOGIN_URL", f"{BASE_URL}/login")
API_BASE_URL = os.environ.get("GAME_API_BASE_URL", f"{BASE_URL}/api")

TARGET_MAP = os.environ.get("GAME_TARGET_MAP", "Vùng Johto").strip('"\' ')
maps_json_path = Path(__file__).parent / "maps.json"

try:
    with open(maps_json_path, encoding='utf-8') as f:
        maps_data = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"[config] Missing maps.json at {maps_json_path}. Please run python tools/parse_maps.py first.")

if TARGET_MAP not in maps_data:
    raise ValueError(f"[config] Unknown map '{TARGET_MAP}'. Valid maps are: {', '.join(maps_data.keys())}")

map_info = maps_data[TARGET_MAP]
if not map_info.get("unlocked", False):
    raise ValueError(f"[config] Map '{TARGET_MAP}' is LOCKED! Requirement: {map_info.get('requirement', 'Unknown')}")

MAP_URL = BASE_URL + map_info["url"]


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
