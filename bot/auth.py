"""
auth.py – Login and initial navigation.

Contains:
    • login_and_navigate(page)  – fill credentials, submit, go to Johto map
"""

import logging
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

import config
from utils import random_delay

log = logging.getLogger(__name__)


def login_and_navigate(page: Page) -> None:
    """
    Navigate to the login page, fill credentials, submit, then go to the Johto map.
    Raises PlaywrightTimeoutError if any step times out.
    """
    # ── Open login page ──────────────────────────────────────────────────────
    log.info("[auth] Navigating to login page: %s", config.LOGIN_URL)
    page.goto(config.LOGIN_URL, wait_until="domcontentloaded")
    random_delay()

    # ── Fill email ───────────────────────────────────────────────────────────
    log.info("[auth] Filling email...")
    email_input = page.get_by_label("Email", exact=False)
    if not email_input.is_visible(timeout=4_000):
        email_input = page.locator(
            "input[type='email'], input[name='email'], input[name='username']"
        ).first
    email_input.wait_for(state="visible", timeout=15_000)
    email_input.fill(config.EMAIL)
    random_delay()

    # ── Fill password ─────────────────────────────────────────────────────────
    log.info("[auth] Filling password...")
    password_input = page.get_by_label("Password", exact=False)
    if not password_input.is_visible(timeout=4_000):
        password_input = page.locator("input[type='password']").first
    password_input.wait_for(state="visible", timeout=10_000)
    password_input.fill(config.PASSWORD)
    random_delay()

    # ── Click login button ───────────────────────────────────────────────────
    log.info("[auth] Clicking 'Đăng Nhập'...")
    login_button = page.get_by_role("button", name="Đăng Nhập")
    login_button.wait_for(state="visible", timeout=10_000)
    login_button.click()
    page.wait_for_load_state("networkidle", timeout=30_000)
    random_delay()

    current_url = page.url
    if "login" in current_url.lower():
        log.warning("[auth] Still on login page – credentials may be wrong.")
    else:
        log.info("[auth] Login successful! URL: %s", current_url)

    # ── Navigate to map ──────────────────────────────────────────────────────
    log.info("[auth] Navigating to Johto map: %s", config.MAP_URL)
    page.goto(config.MAP_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=30_000)
    log.info("[auth] Arrived at Johto map.")
    random_delay()
