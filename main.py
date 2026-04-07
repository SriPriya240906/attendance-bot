import argparse
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot import send_attendance_screenshot, send_error_message
from config import TIMEZONE, logger
from scraper import capture_attendance_screenshot, prune_old_screenshots


async def run_daily_report() -> None:
    date_label = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    logger.info("Starting scheduled attendance report for %s", date_label)
    try:
        screenshot_path = await capture_attendance_screenshot()
        caption = f"Daily Attendance Report - {date_label}"
        send_attendance_screenshot(screenshot_path, caption)
        prune_old_screenshots(max_keep=7)
        logger.info("Daily report completed successfully")
    except Exception as exc:
        message = f"Attendance automation failed: {exc}"
        logger.exception(message)
        try:
            send_error_message(message)
        except Exception as nested_exc:
            logger.error("Failed to send error message to Telegram: %s", nested_exc)


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    trigger = CronTrigger(hour=15, minute=30, timezone=TIMEZONE)
    scheduler.add_job(
        run_daily_report,
        trigger=trigger,
        id="attendance_report",
        replace_existing=True
    )
    return scheduler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RIT Chennai IMS Attendance Automation")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Trigger the attendance report immediately instead of waiting for the scheduled time.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.run_now:
        await run_daily_report()
        return

    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    logger.info("Application running in cloud mode (Railway)")
    
    # Log next scheduled run time
    job = scheduler.get_job("attendance_report")
    if job:
        next_run = job.next_run_time
        if next_run:
            logger.info("Next scheduled run: %s", next_run.strftime("%Y-%m-%d %H:%M:%S %Z"))

    # Keep the app running indefinitely in production
    while True:
        await asyncio.sleep(3600)  # Sleep for 1 hour, can be interrupted for graceful shutdown


if __name__ == "__main__":
    asyncio.run(main())
