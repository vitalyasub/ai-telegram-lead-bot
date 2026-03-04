import asyncio

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
)

from config import ADMIN_ID, BUTTON_TEXT, WELCOME_TEXT, SUCCESS_TEXT

router = Router()


# --- Клавіатури ---
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
        [KeyboardButton(text="⬅️ Назад")],
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


# --- Admin FSM ---
class AdminStates(StatesGroup):
    phone_search = State()


# --- Lead FSM ---
class LeadForm(StatesGroup):
    name = State()
    phone = State()
    comment = State()
    confirm = State()


def _is_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == ADMIN_ID)


def _normalize_phone(raw: str) -> str:
    raw = (raw or "").strip()
    cleaned = []
    for ch in raw:
        if ch.isdigit() or ch == "+":
            cleaned.append(ch)
    return "".join(cleaned)


# --- Global cancel (працює з будь-якого стану) ---
@router.message(Command("cancel"))
@router.message(lambda m: (m.text or "").strip().lower() == "скасувати")
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Ок, скасовано. Повертаю в головне меню.", reply_markup=main_kb)


# --- Start ---
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=main_kb)


# --- Admin panel ---
@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not _is_admin(message):
        return
    await state.clear()
    await message.answer("Адмін-панель:", reply_markup=admin_kb)


@router.message(Command("stats"))
async def admin_stats(message: Message, state: FSMContext):
    if not _is_admin(message):
        return

    try:
        stats = await asyncio.to_thread(get_leads_stats)
    except Exception as e:
        await message.answer(f"⚠️ Не вдалося отримати статистику: {e}", reply_markup=admin_kb)
        return

    await message.answer(
        "📊 Статистика заявок:\n\n"
        f"• Всього: {stats.get('total', 0)}\n"
        f"• Сьогодні: {stats.get('today', 0)}\n"
        f"• Останні 7 днів: {stats.get('last_7_days', 0)}",
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

    try:
        rows = await asyncio.to_thread(get_last_leads, 10)
    except Exception as e:
        await message.answer(f"⚠️ Не вдалося отримати заявки: {e}", reply_markup=admin_kb)
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
    except Exception as e:
        await message.answer(f"⚠️ Помилка пошуку: {e}", reply_markup=admin_kb)
        await state.clear()
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


# --- Lead flow ---
@router.message(lambda m: (m.text or "") == BUTTON_TEXT)
async def start_lead_form(message: Message, state: FSMContext):
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
    await message.answer("Вкажіть номер телефону (наприклад: +380XXXXXXXXX):", reply_markup=cancel_kb)


@router.message(LeadForm.phone)
async def process_phone(message: Message, state: FSMContext):
    phone_raw = message.text or ""
    phone = _normalize_phone(phone_raw)

    digits = [c for c in phone if c.isdigit()]
    if len(digits) < 10:
        await message.answer(
            "Схоже, номер некоректний. Вкажіть телефон ще раз (мінімум 10 цифр):",
            reply_markup=cancel_kb
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(LeadForm.comment)
    await message.answer("Додайте коментар до заявки (або напишіть: Без коментаря):", reply_markup=cancel_kb)


@router.message(LeadForm.comment)
async def process_comment(message: Message, state: FSMContext):
    comment = (message.text or "").strip()
    if not comment:
        comment = "Без коментаря"

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
    username = message.from_user.username if message.from_user else None

    # 1) Запис в Sheets
    try:
        await asyncio.to_thread(
            append_lead_row,
            name=name,
            phone=phone,
            comment=comment,
            username=username,
        )
    except Exception as e:
        await message.bot.send_message(ADMIN_ID, f"⚠️ Помилка запису в Google Sheets: {e}")

    # 2) Адміну
    await message.bot.send_message(
        ADMIN_ID,
        "📩 Нова заявка!\n\n"
        f"👤 Ім’я: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📝 Коментар: {comment}"
    )

    # 3) Користувачу
    await state.clear()
    await message.answer(
        f"{SUCCESS_TEXT}\n\n"
        f"👤 Ім’я: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📝 Коментар: {comment}",
        reply_markup=main_kb
    )