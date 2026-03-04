from __future__ import annotations

from datetime import datetime, timedelta
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

from typing import List, Dict, Any

def get_last_leads(limit: int = 10) -> list[list[str]]:
    client = _get_client()
    sh = client.open(GSHEET_NAME)
    ws = sh.sheet1

    values = ws.get_all_values()  # включно з хедером
    if not values:
        return []

    rows = values[1:]  # без хедера
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    return rows[-limit:]


def find_leads_by_phone(phone_query: str, limit: int = 5) -> list[list[str]]:
    client = _get_client()
    sh = client.open(GSHEET_NAME)
    ws = sh.sheet1

    values = ws.get_all_values()
    if not values:
        return []

    rows = values[1:]
    q = phone_query.strip()
    found = []
    for r in rows:
        # колонки: дата, ім’я, телефон, коментар, username
        phone = r[2] if len(r) > 2 else ""
        if q and q in phone:
            found.append(r)
            if len(found) >= limit:
                break
    return found

def get_leads_stats() -> dict[str, int]:
    """
    Повертає статистику по заявках:
    - total: всього
    - today: сьогодні
    - last_7_days: за останні 7 днів
    Очікує формат дати/часу в колонці 1: "%Y-%m-%d %H:%M:%S"
    """
    client = _get_client()
    sh = client.open(GSHEET_NAME)
    ws = sh.sheet1

    values = ws.get_all_values()
    if not values:
        return {"total": 0, "today": 0, "last_7_days": 0}

    rows = values[1:]  # без хедера
    rows = [r for r in rows if any(cell.strip() for cell in r)]

    total = len(rows)

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    week_ago = now - timedelta(days=7)

    today_count = 0
    last_7_days_count = 0

    for r in rows:
        dt_str = r[0] if len(r) > 0 else ""
        if not dt_str:
            continue

        # today
        if dt_str.startswith(today_str):
            today_count += 1

        # last 7 days
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            if dt >= week_ago:
                last_7_days_count += 1
        except ValueError:
            # Якщо дата в іншому форматі — просто пропускаємо
            pass

    return {"total": total, "today": today_count, "last_7_days": last_7_days_count}