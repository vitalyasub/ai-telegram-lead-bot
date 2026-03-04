import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN

from handlers import router
from sheets import ensure_header

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(router)

    # Ініціалізація таблиці (хедер)
    await asyncio.to_thread(ensure_header)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())