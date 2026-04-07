import asyncio
import logging
import re
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
    date_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    filename = f"attendance_{date_str}.png"
    return SCREENSHOT_DIR / filename


def _add_watermark(image_path: Path, watermark_text: str) -> None:
    logger.info("Adding watermark to screenshot")
    with Image.open(image_path).convert("RGBA") as image:
        txt = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt)
        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except Exception:
            font = ImageFont.load_default()

        margin = 12
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = margin
        y = image.height - text_height - margin
        draw.rectangle(
            [(x - 6, y - 6), (x + text_width + 6, y + text_height + 6)],
            fill=(0, 0, 0, 120),
        )
        draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 230))
        combined = Image.alpha_composite(image, txt)
        combined.convert("RGB").save(image_path, quality=90)


def prune_old_screenshots(max_keep: int = 7) -> None:
    screenshots = sorted(
        SCREENSHOT_DIR.glob("attendance_*.png"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    old_files = screenshots[max_keep:]
    for old_file in old_files:
        try:
            logger.info("Removing old screenshot: %s", old_file.name)
            old_file.unlink()
        except Exception as exc:
            logger.warning("Could not remove old screenshot %s: %s", old_file.name, exc)


async def _login(page) -> None:
    logger.info("Waiting for login form")
    username_locator = page.locator('input[type="text"], input[type="email"], input[name*="user"], input[id*="user"]')
    password_locator = page.locator('input[type="password"], input[name*="pass"], input[id*="pass"]')
    login_button_locator = page.locator('button[type=submit], input[type=submit]').or_(page.locator('button:has-text("Login")')).or_(page.locator('input[value*="Login"]'))

    await username_locator.first.wait_for(state="visible", timeout=30000)
    await password_locator.first.wait_for(state="visible", timeout=30000)

    username = get_env("IMS_USERNAME")
    password = get_env("IMS_PASSWORD")

    await username_locator.first.fill(username)
    await password_locator.first.fill(password)
    await asyncio.sleep(0.5)
    await login_button_locator.first.click()
    await page.wait_for_load_state("networkidle", timeout=30000)


async def _navigate_to_attendance(page) -> Optional[object]:
    logger.info("Navigating to Attendance section")
    attendance_text = re.compile(r"attendance", re.I)
    clicked = False

    for role_name in ["link", "button"]:
        elements = page.get_by_role(role_name, name=attendance_text)
        if await elements.count() > 0:
            await elements.first.wait_for(state="visible", timeout=20000)
            await elements.first.click()
            clicked = True
            break

    if not clicked:
        text_elements = page.get_by_text(attendance_text)
        if await text_elements.count() > 0:
            await text_elements.first.wait_for(state="visible", timeout=20000)
            await text_elements.first.click()
            clicked = True

    if not clicked:
        logger.warning("Attendance navigation element not found. Attempting URL fallback.")
        await page.goto(f"{IMS_URL}/student/attendance", wait_until="networkidle", timeout=30000)
    else:
        await page.wait_for_load_state("networkidle", timeout=30000)
        if "attendance" not in page.url.lower():
            logger.warning("Attendance click did not reach attendance URL; using fallback.")
            await page.goto(f"{IMS_URL}/student/attendance", wait_until="networkidle", timeout=30000)

    await page.wait_for_load_state("networkidle", timeout=30000)
    attendance_header = page.get_by_text(attendance_text)
    await attendance_header.first.wait_for(state="visible", timeout=30000)

    container = page.locator('section:has-text("Attendance")').or_(page.locator('div:has-text("Attendance")')).or_(page.locator('table:has-text("Attendance")')).or_(page.locator('.attendance'))
    await container.first.wait_for(state="visible", timeout=30000)
    return container.first


async def capture_attendance_screenshot() -> str:
    last_error = None
    output_path = _build_screenshot_filename()

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            async with async_playwright() as playwright:
                browser: Browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(ignore_https_errors=True)
                page = await context.new_page()
                page.set_default_timeout(45000)

                logger.info("Opening IMS portal: %s", IMS_URL)
                await page.goto(IMS_URL, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                await _login(page)
                attendance_locator = await _navigate_to_attendance(page)

                if attendance_locator:
                    logger.info("Capturing full attendance page screenshot")
                    await page.screenshot(path=str(output_path), full_page=True)
                else:
                    logger.warning("Attendance container not located; capturing full page screenshot")
                    await page.screenshot(path=str(output_path), full_page=True)

                watermark_text = f"Attendance captured on {_timestamp_text()}"
                _add_watermark(output_path, watermark_text)

                await context.close()
                await browser.close()

                logger.info("Screenshot saved to %s", output_path)
                return str(output_path)
        except (PlaywrightTimeoutError, PlaywrightError, Exception) as exc:
            last_error = exc
            logger.warning("Attempt %s failed: %s", attempt, exc)
            if attempt <= MAX_RETRIES:
                await asyncio.sleep(5)
                logger.info("Retrying login and capture (attempt %s)", attempt + 1)
            else:
                logger.error("All capture attempts failed")

    raise RuntimeError(f"Attendance screenshot capture failed: {last_error}")
