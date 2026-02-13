import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Session Configuration
# SESSION_STRING: Telethon StringSession (recommended for Heroku/cloud deployments)
# If SESSION_STRING is provided, it will be used instead of file-based session
SESSION_STRING = os.getenv("SESSION_STRING", "")

# PHONE_NUMBER: Only needed for generating new session string
# Not required if SESSION_STRING is already provided
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")

# SESSION_NAME: Used as fallback for file-based session (local development only)
SESSION_NAME = os.getenv("SESSION_NAME", "forwarder_session")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Bot Settings
BOT_RECONNECT_DELAY = int(os.getenv("BOT_RECONNECT_DELAY", "5"))  # seconds
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))  # seconds
