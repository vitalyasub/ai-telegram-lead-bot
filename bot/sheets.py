from __future__ import annotations

from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

from config import GSHEET_NAME, GOOGLE_CREDS_PATH


def _get_client() -> gspread.Client:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=scopes)
    return gspread.authorize(creds)


def ensure_header() -> None:
    client = _get_client()
    sh = client.open(GSHEET_NAME)
    ws = sh.sheet1

    header = ["Дата/час", "Ім’я", "Телефон", "Коментар", "Username"]
    first_row = ws.row_values(1)

    if first_row != header:
        ws.insert_row(header, 1)


def append_lead_row(
    *,
    name: str,
    phone: str,
    comment: str,
    username: str | None,
) -> None:
    client = _get_client()
    sh = client.open(GSHEET_NAME)
    ws = sh.sheet1

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([now, name, phone, comment, username or ""], value_input_option="USER_ENTERED")