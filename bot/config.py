import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

GSHEET_NAME = os.getenv("GSHEET_NAME")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "credentials.json")