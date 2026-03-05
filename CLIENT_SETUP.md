# Налаштування бота для клієнта (Client Setup)

Цей документ описує, що потрібно для запуску Telegram Lead Bot під конкретний бізнес.

---

## 1) Що потрібно від клієнта

1. Тексти (або підтвердження стандартних):
   - привітальне повідомлення
   - текст кнопки
   - текст після успішної заявки
2. Google-акаунт (або доступ до таблиці), де буде зберігатися база заявок.
3. Telegram-акаунт менеджера/власника (хто отримуватиме заявки).

---

## 2) Створення Telegram-бота

1. В Telegram відкрити @BotFather
2. Команда `/newbot`
3. Отримати `BOT_TOKEN`

---

## 3) Google Sheets (CRM)

1. Створити таблицю Google Sheets (наприклад `Leads`)
2. У Google Cloud:
   - увімкнути Google Sheets API
   - увімкнути Google Drive API
   - створити Service Account
   - створити JSON ключ (credentials)
3. Надати доступ до таблиці для `client_email` з JSON ключа (роль Editor)

---

## 4) Файл `.env`

Створити `.env` у корені проєкту:

```env
BOT_TOKEN=...
ADMIN_ID=...

GSHEET_NAME=Leads
GOOGLE_CREDS_PATH=credentials.json

BOT_NAME=Lead Bot
WELCOME_TEXT=Вітаю! 👋 Натисніть кнопку нижче щоб залишити заявку.
BUTTON_TEXT=Залишити заявку
SUCCESS_TEXT=Дякуємо! Ми зв’яжемося з вами найближчим часом.

LEADS_ENABLED=1
LEAD_COOLDOWN_MINUTES=30