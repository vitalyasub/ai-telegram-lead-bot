import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "bot.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Логи в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Логи у файл з ротацією
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,   # ~1MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Щоб не дублювало хендлери при повторному запуску
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    # Трохи притишимо зайве від бібліотек
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)