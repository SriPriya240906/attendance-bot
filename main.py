import argparse
import asyncio
from datetime import datetime

from bot import send_attendance_screenshot, send_error_message
from config import TIMEZONE, logger
from scraper import capture_attendance_screenshot, prune_old_screenshots


async def run_daily_report() -> None:
    date_label = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    logger.info("Starting attendance report for %s", date_label)
    try:
        screenshot_path = await capture_attendance_screenshot()
        caption = f"Attendance Report - {date_label}"
        send_attendance_screenshot(screenshot_path, caption)
        prune_old_screenshots(max_keep=7)
        logger.info("Report sent successfully")
    except Exception as exc:
        message = f"Attendance automation failed: {exc}"
        logger.exception(message)
        try:
            send_error_message(message)
        except Exception as nested_exc:
            logger.error("Telegram error: %s", nested_exc)


async def main():
    await run_daily_report()


if __name__ == "__main__":
    asyncio.run(main())
