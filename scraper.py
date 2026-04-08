import asyncio
import logging
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright, Browser, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from config import SCREENSHOT_DIR, TIMEZONE, get_env, logger

IMS_URL = "https://ims.ritchennai.edu.in"
MAX_RETRIES = 2


def _timestamp_text() -> str:
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S IST")


def _build_screenshot_filename() -> Path:
    date_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d_%H-%M-%S")
    return SCREENSHOT_DIR / f"attendance_{date_str}.png"


def _add_watermark(image_path: Path, watermark_text: str) -> None:
    with Image.open(image_path).convert("RGBA") as image:
        txt = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt)

        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except:
            font = ImageFont.load_default()

        margin = 12
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        x = margin
        y = image.height - (bbox[3] - bbox[1]) - margin

        draw.rectangle(
            [(x - 6, y - 6), (x + (bbox[2] - bbox[0]) + 6, y + (bbox[3] - bbox[1]) + 6)],
            fill=(0, 0, 0, 120),
        )

        draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 230))
        combined = Image.alpha_composite(image, txt)
        combined.convert("RGB").save(image_path, quality=90)


async def _login(page) -> None:
    print("🔐 Waiting for login form...")

    await page.wait_for_selector('input[type="password"]', timeout=30000)

    username = get_env("IMS_USERNAME")
    password = get_env("IMS_PASSWORD")

    await page.fill('input[type="text"], input[type="email"]', username)
    await page.fill('input[type="password"]', password)

    await page.click('button[type=submit], input[type=submit]')
    await page.wait_for_load_state("networkidle")

    # ✅ VERIFY LOGIN
    if "login" in page.url.lower():
        raise Exception("❌ Login failed")

    print("✅ Login successful")


async def _navigate_to_attendance(page):
    print("📍 Navigating to attendance...")

    await asyncio.sleep(3)

    try:
        await page.click("text=Attendance", timeout=15000)
    except:
        print("⚠️ Direct click failed, using fallback URL")
        await page.goto(f"{IMS_URL}/student/attendance")

    await page.wait_for_load_state("networkidle")

    print("✅ Attendance page loaded:", page.url)


async def capture_attendance_screenshot() -> str:
    output_path = _build_screenshot_filename()
    last_error = None

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            print(f"🚀 Attempt {attempt}")

            async with async_playwright() as p:
                browser: Browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(ignore_https_errors=True)
                page = await context.new_page()

                await page.goto(IMS_URL, timeout=45000)

                await _login(page)
                await _navigate_to_attendance(page)

                # ⏳ Extra wait for rendering
                await page.wait_for_timeout(5000)

                print("📸 Taking screenshot...")

                await page.screenshot(path=str(output_path), full_page=True)

                # ✅ VERIFY FILE
                if not os.path.exists(output_path):
                    raise Exception("❌ Screenshot not created")

                print("✅ Screenshot saved:", output_path)

                _add_watermark(output_path, f"Captured on {_timestamp_text()}")

                await browser.close()
                return str(output_path)

        except Exception as e:
            last_error = e
            print(f"❌ Attempt {attempt} failed:", e)

            if attempt <= MAX_RETRIES:
                await asyncio.sleep(5)
            else:
                raise RuntimeError(f"❌ All attempts failed: {last_error}")
