import logging
import requests

from config import get_env, logger

TELEGRAM_API_TOKEN = get_env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_env("TELEGRAM_CHAT_ID")
TELEGRAM_BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}"


def send_error_message(message: str) -> None:
    logger.info("Sending Telegram error message")
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }
    response = requests.post(f"{TELEGRAM_BASE_URL}/sendMessage", json=payload, timeout=30)
    if not response.ok:
      logger.error("Telegram API error: %s", response.text)
      return   # instead of raise_for_status()

def send_attendance_screenshot(image_path: str, caption: str) -> None:
    logger.info("Sending attendance screenshot to Telegram: %s", image_path)
    with open(image_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption,
        }
        response = requests.post(
            f"{TELEGRAM_BASE_URL}/sendPhoto",
            data=data,
            files=files,
            timeout=60,
        )
    if not response.ok:
        logger.error("Telegram API error: %s", response.text)
        response.raise_for_status()
    logger.info("Telegram photo sent successfully")
