import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from logging_config import setup_logging
from config import BOT_TOKEN
from handlers import router
from sheets import ensure_header


async def main():
    setup_logging()
    logger = logging.getLogger("bot")

    logger.info("Запуск бота...")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # Ініціалізація таблиці (хедер) — не зупиняємо бота, якщо Google тимчасово недоступний
    try:
        await asyncio.to_thread(ensure_header)
        logger.info("Google Sheet ініціалізовано (хедер перевірено)")
    except Exception:
        logger.exception("Не вдалося ініціалізувати Google Sheet (ensure_header). Бот стартує без цього.")

    try:
        await dp.start_polling(bot)
    except Exception:
        logger.exception("Критична помилка під час роботи бота")
        raise
    finally:
        # Коректно закриваємо HTTP-сесію бота
        await bot.session.close()
        logger.info("Зупинка бота")


if __name__ == "__main__":
    asyncio.run(main())