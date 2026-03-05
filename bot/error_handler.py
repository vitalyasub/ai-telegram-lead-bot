import logging
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

from config import ADMIN_ID

router = Router()
logger = logging.getLogger("bot.errors")

# антиспам для повідомлень адміну про помилки
_last_notify_at: datetime | None = None
_NOTIFY_COOLDOWN = timedelta(minutes=2)


def _should_notify_admin() -> bool:
    global _last_notify_at
    now = datetime.now()
    if _last_notify_at is None or (now - _last_notify_at) >= _NOTIFY_COOLDOWN:
        _last_notify_at = now
        return True
    return False


@router.errors()
async def global_error_handler(event: ErrorEvent) -> bool:
    """
    Глобальний обробник помилок aiogram 3.
    Повертаємо True -> помилка вважається обробленою (не "пробивається" далі).
    """
    exc = event.exception

    # Логуємо повний stack trace
    logger.exception("Необроблена помилка в боті: %r", exc)

    # Спробуємо витягнути трохи контексту
    user_id = None
    username = None
    text = None

    try:
        update = event.update
        if update and update.message:
            user = update.message.from_user
            if user:
                user_id = user.id
                username = user.username
            text = update.message.text
    except Exception:
        # якщо контекст недоступний — просто мовчки
        pass

    # Коротке повідомлення адміну (обмежуємо частоту)
    if _should_notify_admin():
        try:
            short = (
                "⚠️ Виникла помилка в боті.\n\n"
                f"Тип: {type(exc).__name__}\n"
                f"Текст: {str(exc)[:300]}\n"
            )
            if user_id or text:
                short += "\nКонтекст:\n"
                if user_id:
                    short += f"• user_id: {user_id}\n"
                if username:
                    short += f"• username: @{username}\n"
                if text:
                    short += f"• message: {text[:200]}\n"

            # event.update може не мати bot-а, тому беремо через event.update.*
            bot = event.update.bot if event.update else None
            if bot:
                await bot.send_message(ADMIN_ID, short)
        except TelegramAPIError:
            # якщо телеграм тимчасово не дає відправити — не падаємо
            logger.warning("Не вдалося надіслати алерт адміну через TelegramAPIError")
        except Exception:
            logger.exception("Не вдалося надіслати алерт адміну")

    return True