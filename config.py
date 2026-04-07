import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
SCREENSHOT_DIR = BASE_DIR / "screenshots"
ENV_PATH = BASE_DIR / ".env"
LOG_FILE = LOG_DIR / "app.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv()

TIMEZONE = ZoneInfo("Asia/Kolkata")

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("rit-ims-agent")


def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "")
    if required and not value:
        message = f"Environment variable {name} is missing or empty."
        logger.error(message)
        raise EnvironmentError(message)
    return value.strip()
