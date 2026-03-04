from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

# user_id -> datetime останньої підтвердженої заявки
_last_submit: Dict[int, datetime] = {}


def can_submit(user_id: int, cooldown_minutes: int) -> tuple[bool, int]:
    """
    Повертає (можна_відправляти, скільки_хвилин_залишилось).
    """
    now = datetime.now()
    last = _last_submit.get(user_id)
    if not last:
        return True, 0

    cooldown = timedelta(minutes=cooldown_minutes)
    next_time = last + cooldown
    if now >= next_time:
        return True, 0

    remaining = next_time - now
    remaining_minutes = max(1, int(remaining.total_seconds() // 60) + 1)
    return False, remaining_minutes


def mark_submitted(user_id: int) -> None:
    _last_submit[user_id] = datetime.now()