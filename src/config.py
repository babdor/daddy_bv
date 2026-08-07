import logging
import os
import sys

# ------------------------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------------------------
LOG_FILE = os.getenv("LOG_FILE", "/app/logs/bot.log")

log_dir = os.path.dirname(LOG_FILE)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)

logger = logging.getLogger("MeshtasticAIBot")

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ------------------------------------------------------------------------------
# Configuration & Constants
# ------------------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")

MODEL_NAME = "gemma4:31b"
TARGET_CHANNEL_INDEX = 0  # Primary Channel (DEFCONnect)
BOT_HANDLE = "ddbv"

# Context & Conversational Flow Range Settings
MAX_CONTEXT_MESSAGES = 15       # Sliding window size

# Dynamic Threshold Bounds (Message Count)
MIN_TRIGGER_THRESHOLD = 4       # Min incoming messages before passive reply
MAX_TRIGGER_THRESHOLD = 12      # Max incoming messages before passive reply

# Dynamic Cooldown Bounds (Seconds)
MIN_COOLDOWN_SECONDS = 15       # Min delay between transmissions
MAX_COOLDOWN_SECONDS = 180      # Max delay between transmissions

# Dry Heat Phrases
DRY_HEAT_RESPONSES = [
    "Yeah, but it's a dry heat.",
    "At least it's a dry heat...",
    "Don't worry, it's a dry heat.",
    "Sure, but it's a dry heat out here.",
]
