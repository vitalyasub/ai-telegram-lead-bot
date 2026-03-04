import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

GSHEET_NAME = os.getenv("GSHEET_NAME")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "credentials.json")

BOT_NAME = os.getenv("BOT_NAME", "Lead Bot")
WELCOME_TEXT = os.getenv("WELCOME_TEXT", "Вітаю!")
BUTTON_TEXT = os.getenv("BUTTON_TEXT", "Залишити заявку")
SUCCESS_TEXT = os.getenv("SUCCESS_TEXT", "Дякуємо!")

LEADS_ENABLED = os.getenv("LEADS_ENABLED", "1") == "1"
LEAD_COOLDOWN_MINUTES = int(os.getenv("LEAD_COOLDOWN_MINUTES", "30"))