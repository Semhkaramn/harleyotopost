import os
from dotenv import load_dotenv

load_dotenv()

# Bot Token (@BotFather'dan alınır)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Bot Settings
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
