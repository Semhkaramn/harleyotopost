import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")
SESSION_NAME = os.getenv("SESSION_NAME", "forwarder_session")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")
