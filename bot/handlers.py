import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from sheets import (
    append_lead_row,
    get_last_leads,
    find_leads_by_phone,
    get_leads_stats,
    ping_sheets,
)

from config import (
    ADMIN_ID,
    BUTTON_TEXT,
    WELCOME_TEXT,
    SUCCESS_TEXT,
    LEADS_ENABLED,
    LEAD_COOLDOWN_MINUTES,
)

from rate_limit import can_submit, mark_submitted
from runtime_flags import is_leads_enabled, set_leads_enabled

router = Router()
logger = logging.getLogger("bot.handlers")


# =========================
# Клавіатури
# =========================
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BUTTON_TEXT)]],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Скасувати")]],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📄 Останні 10 заявок")],
        [KeyboardButton(text="🔎 Пошук за телефоном")],
        [KeyboardButton(text="📴 Прийом заявок: статус")],
        [KeyboardButton(text="🔁 Перемкнути прийом заявок")],
        [KeyboardButton(text="⬅️ Назад")],
    ],
    resize_keyboard=True
)

contact_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📲 Поділитися контактом", request_contact=True)],
        [KeyboardButton(text="Скасувати")],
    ],
    resize_keyboard=True
)

confirm_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Підтвердити")],
        [KeyboardButton(text="✏️ Заповнити заново")],
        [KeyboardButton(text="Скасувати")],
    ],
    resize_keyboard=True
)


# =========================
# FSM
# =========================
class AdminStates(StatesGroup):
    phone_search = State()


class LeadForm(StatesGroup):
    name = State()
    phone = State()
    comment = State()
    confirm = State()


# =========================
# Helpers
# =========================
def _is_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == ADMIN_ID)


def _normalize_phone(raw: str) -> str:
    raw = (raw or "").strip()
    cleaned = []
    for ch in raw:
        if ch.isdigit() or ch == "+":
            cleaned.append(ch)
    return "".join(cleaned)


async def _cancel_to_correct_menu(message: Message, state: FSMContext) -> None:
    """
    Контекстна відміна:
    - якщо адмін — повертаємо admin_kb
    - інакше — main_kb
    """
    await state.clear()
    if _is_admin(message):
        await message.answer("Ок, скасовано.", reply_markup=admin_kb)
    else:
        await message.answer("Ок, скасовано. Повертаю в головне меню.", reply_markup=main_kb)


# =========================
# Global cancel
# =========================
@router.message(Command("cancel"))
@router.message(lambda m: (m.text or "").strip().lower() == "скасувати")
async def cancel_any(message: Message, state: FSMContext):
    logger.info(
        "Cancel | user_id=%s username=%s state=%s",
        message.from_user.id if message.from_user else 0,
        message.from_user.username if message.from_user else None,
        await state.get_state()
    )
    await _cancel_to_correct_menu(message, state)


# =========================
# Start
# =========================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=main_kb)


# =========================
# Admin
# =========================
@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not _is_admin(message):
        return
    logger.info("Admin /admin | admin_id=%s", message.from_user.id)
    await state.clear()
    await message.answer("Адмін-панель:", reply_markup=admin_kb)


@router.message(Command("stats"))
async def admin_stats(message: Message, state: FSMContext):
    if not _is_admin(message):
        return
    logger.info("Admin /stats | admin_id=%s", message.from_user.id)

    try:
        stats = await asyncio.to_thread(get_leads_stats)
    except Exception:
        logger.exception("Admin /stats failed")
        await message.answer("⚠️ Не вдалося отримати статистику.", reply_markup=admin_kb)
        return

    await message.answer(
        "📊 Статистика заявок:\n\n"
        f"• Всього: {stats.get('total', 0)}\n"
        f"• Сьогодні: {stats.get('today', 0)}\n"
        f"• Останні 7 днів: {stats.get('last_7_days', 0)}",
        reply_markup=admin_kb
    )

@router.message(Command("health"))
async def admin_health(message: Message, state: FSMContext):
    if not _is_admin(message):
        return

    enabled = await asyncio.to_thread(is_leads_enabled, LEADS_ENABLED)
    ok_sheets, sheets_msg = await asyncio.to_thread(ping_sheets)

    await message.answer(
        "🩺 Health check:\n\n"
        f"• Bot: OK ✅\n"
        f"• Прийом заявок: {'УВІМКНЕНО ✅' if enabled else 'ВИМКНЕНО ❌'}\n"
        f"• Cooldown: {LEAD_COOLDOWN_MINUTES} хв\n"
        f"• Google Sheets: {'OK ✅' if ok_sheets else 'ERROR ❌'}\n"
        f"  {sheets_msg}\n",
        reply_markup=admin_kb
    )

@router.message(lambda m: (m.text or "") == "⬅️ Назад")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Головне меню:", reply_markup=main_kb)


@router.message(lambda m: (m.text or "") == "📄 Останні 10 заявок")
async def admin_last_leads(message: Message, state: FSMContext):
    if not _is_admin(message):
        return
    logger.info("Admin last leads | admin_id=%s", message.from_user.id)

    try:
        rows = await asyncio.to_thread(get_last_leads, 10)
    except Exception:
        logger.exception("Admin last leads failed")
        await message.answer("⚠️ Не вдалося отримати заявки.", reply_markup=admin_kb)
        return

    if not rows:
        await message.answer("Поки що заявок немає.", reply_markup=admin_kb)
        return

    text_lines = ["📄 Останні заявки:"]
    for r in rows:
        dt = r[0] if len(r) > 0 else "—"
        name = r[1] if len(r) > 1 else "—"
        phone = r[2] if len(r) > 2 else "—"
        comment = r[3] if len(r) > 3 else "—"
        text_lines.append(f"\n🕒 {dt}\n👤 {name}\n📞 {phone}\n📝 {comment}")

    await message.answer("\n".join(text_lines), reply_markup=admin_kb)


@router.message(lambda m: (m.text or "") == "🔎 Пошук за телефоном")
async def admin_search_phone_start(message: Message, state: FSMContext):
    if not _is_admin(message):
        return

    await state.set_state(AdminStates.phone_search)
    await message.answer(
        "Введіть частину номера телефону для пошуку (наприклад: 067 або +38067):",
        reply_markup=cancel_kb
    )


@router.message(AdminStates.phone_search)
async def admin_search_phone_process(message: Message, state: FSMContext):
    if not _is_admin(message):
        return

    q = (message.text or "").strip()
    if len(q) < 3:
        await message.answer("Запит закороткий. Введіть мінімум 3 символи номера:", reply_markup=cancel_kb)
        return

    try:
        rows = await asyncio.to_thread(find_leads_by_phone, q, 5)
    except Exception:
        logger.exception("Admin search failed | q=%s", q)
        await state.clear()
        await message.answer("⚠️ Помилка пошуку.", reply_markup=admin_kb)
        return

    await state.clear()

    if not rows:
        await message.answer("Нічого не знайдено.", reply_markup=admin_kb)
        return

    text_lines = ["🔎 Знайдено (до 5):"]
    for r in rows:
        dt = r[0] if len(r) > 0 else "—"
        name = r[1] if len(r) > 1 else "—"
        phone = r[2] if len(r) > 2 else "—"
        comment = r[3] if len(r) > 3 else "—"
        text_lines.append(f"\n🕒 {dt}\n👤 {name}\n📞 {phone}\n📝 {comment}")

    await message.answer("\n".join(text_lines), reply_markup=admin_kb)


@router.message(lambda m: (m.text or "") == "📴 Прийом заявок: статус")
async def admin_leads_status(message: Message, state: FSMContext):
    if not _is_admin(message):
        return

    enabled = await asyncio.to_thread(is_leads_enabled, LEADS_ENABLED)
    await message.answer(
        f"🧾 Прийом заявок зараз: {'УВІМКНЕНО ✅' if enabled else 'ВИМКНЕНО ❌'}",
        reply_markup=admin_kb
    )


@router.message(lambda m: (m.text or "") == "🔁 Перемкнути прийом заявок")
async def admin_leads_toggle(message: Message, state: FSMContext):
    if not _is_admin(message):
        return

    current = await asyncio.to_thread(is_leads_enabled, LEADS_ENABLED)
    new_value = not current
    await asyncio.to_thread(set_leads_enabled, new_value)
    logger.info("Admin toggled leads | enabled=%s", new_value)

    await message.answer(
        f"Готово. Прийом заявок: {'УВІМКНЕНО ✅' if new_value else 'ВИМКНЕНО ❌'}",
        reply_markup=admin_kb
    )


# =========================
# Lead flow
# =========================
@router.message(lambda m: (m.text or "") == BUTTON_TEXT)
async def start_lead_form(message: Message, state: FSMContext):
    user_id = message.from_user.id if message.from_user else 0
    username = message.from_user.username if message.from_user else None

    logger.info("Lead form start | user_id=%s username=%s", user_id, username)

    current_state = await state.get_state()
    if current_state is not None:
        await message.answer(
            "Ви вже заповнюєте заявку. Завершіть її або натисніть «Скасувати».",
            reply_markup=cancel_kb
        )
        return

    enabled = await asyncio.to_thread(is_leads_enabled, LEADS_ENABLED)
    if not enabled:
        await message.answer(
            "Наразі прийом заявок тимчасово вимкнено. Спробуйте, будь ласка, пізніше.",
            reply_markup=main_kb
        )
        return

    if user_id:
        ok, remaining = can_submit(user_id, LEAD_COOLDOWN_MINUTES)
        if not ok:
            await message.answer(
                f"Ви вже надсилали заявку нещодавно. Спробуйте знову приблизно через {remaining} хв.",
                reply_markup=main_kb
            )
            return

    await state.set_state(LeadForm.name)
    await message.answer("Напишіть, будь ласка, ваше ім’я:", reply_markup=cancel_kb)


@router.message(LeadForm.name)
async def process_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Ім’я занадто коротке. Спробуйте ще раз:", reply_markup=cancel_kb)
        return

    await state.update_data(name=name)
    await state.set_state(LeadForm.phone)
    await message.answer(
        "Вкажіть номер телефону.\n\n"
        "✅ Найкраще: натисніть «📲 Поділитися контактом».\n"
        "✍️ Або введіть номер вручну (наприклад: +380XXXXXXXXX).",
        reply_markup=contact_kb
    )


@router.message(LeadForm.phone)
async def process_phone(message: Message, state: FSMContext):
    # 1) Контакт-кнопка
    if message.contact and message.contact.phone_number:
        # Захист: контакт повинен належати цьому користувачу
        if message.contact.user_id and message.from_user and message.contact.user_id != message.from_user.id:
            await message.answer(
                "Будь ласка, надішліть *свій* контакт або введіть номер вручну.",
                reply_markup=contact_kb
            )
            return

        raw_phone = message.contact.phone_number.strip()
        digits = "".join(ch for ch in raw_phone if ch.isdigit())
        if len(digits) < 10:
            await message.answer(
                "Схоже, номер некоректний. Спробуйте ще раз або введіть номер вручну.",
                reply_markup=contact_kb
            )
            return

        phone = "+" + digits
        await state.update_data(phone=phone)
        await state.set_state(LeadForm.comment)
        await message.answer(
            "Додайте коментар до заявки (або напишіть: Без коментаря):",
            reply_markup=cancel_kb
        )
        return

    # 2) Ручний ввід
    phone_raw = message.text or ""
    phone = _normalize_phone(phone_raw)

    digits = [c for c in phone if c.isdigit()]
    if len(digits) < 10:
        await message.answer(
            "Схоже, номер некоректний.\n"
            "Спробуйте ще раз або натисніть «📲 Поділитися контактом».",
            reply_markup=contact_kb
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(LeadForm.comment)
    await message.answer(
        "Додайте коментар до заявки (або напишіть: Без коментаря):",
        reply_markup=cancel_kb
    )


@router.message(LeadForm.comment)
async def process_comment(message: Message, state: FSMContext):
    comment = (message.text or "").strip() or "Без коментаря"

    data = await state.get_data()
    name = data.get("name", "—")
    phone = data.get("phone", "—")

    await state.update_data(comment=comment)
    await state.set_state(LeadForm.confirm)

    await message.answer(
        "Перевірте дані заявки:\n\n"
        f"👤 Ім’я: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📝 Коментар: {comment}\n\n"
        "Підтвердити відправку?",
        reply_markup=confirm_kb
    )


@router.message(LeadForm.confirm, lambda m: (m.text or "") == "✏️ Заповнити заново")
async def lead_restart(message: Message, state: FSMContext):
    await state.set_state(LeadForm.name)
    await message.answer("Добре. Напишіть, будь ласка, ваше ім’я:", reply_markup=cancel_kb)


@router.message(LeadForm.confirm, lambda m: (m.text or "") == "✅ Підтвердити")
async def lead_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name", "—")
    phone = data.get("phone", "—")
    comment = data.get("comment", "Без коментаря")

    user_id = message.from_user.id if message.from_user else 0
    username = message.from_user.username if message.from_user else None

    logger.info(
        "Lead confirmed | user_id=%s username=%s name=%s phone=%s",
        user_id, username, name, phone
    )

    # 1) Запис в Sheets
    sheets_ok = True
    try:
        await asyncio.to_thread(
            append_lead_row,
            name=name,
            phone=phone,
            comment=comment,
            username=username,
        )
        logger.info("Sheets write OK | phone=%s", phone)
    except Exception:
        sheets_ok = False
        logger.exception("Sheets write FAILED | phone=%s", phone)

    # 2) Адміну
    admin_text = (
        "📩 Нова заявка!\n\n"
        f"👤 Ім’я: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📝 Коментар: {comment}"
    )
    if not sheets_ok:
        admin_text += "\n\n⚠️ УВАГА: не вдалося записати в Google Sheets (див. лог)."

    await message.bot.send_message(ADMIN_ID, admin_text)

    # 3) Антиспам: фіксуємо лише після відправки адміну
    if user_id:
        mark_submitted(user_id)

    # 4) Користувачу
    await state.clear()
    await message.answer(
        f"{SUCCESS_TEXT}\n\n"
        f"👤 Ім’я: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📝 Коментар: {comment}",
        reply_markup=main_kb
    )