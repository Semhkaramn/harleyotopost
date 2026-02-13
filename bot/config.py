import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Session String (ZORUNLU)
# generate_session.py ile oluşturun
SESSION_STRING = os.getenv("SESSION_STRING", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Bot Settings
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
