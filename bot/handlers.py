from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

router = Router()

# --- Клавіатура головного меню ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Залишити заявку")],
    ],
    resize_keyboard=True
)

# --- Стан машини (FSM) ---
class LeadForm(StatesGroup):
    name = State()
    phone = State()
    comment = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Вітаю! 👋\nЯ можу допомогти залишити заявку.\nНатисніть кнопку нижче.",
        reply_markup=main_kb
    )


@router.message(lambda m: m.text == "Залишити заявку")
async def start_lead_form(message: Message, state: FSMContext):
    await state.set_state(LeadForm.name)
    await message.answer(
        "Напишіть, будь ласка, ваше ім’я:",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(LeadForm.name)
async def process_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()

    if len(name) < 2:
        await message.answer("Ім’я занадто коротке. Спробуйте ще раз:")
        return

    await state.update_data(name=name)
    await state.set_state(LeadForm.phone)
    await message.answer("Вкажіть номер телефону (наприклад: +380XXXXXXXXX):")


def _normalize_phone(raw: str) -> str:
    # Дозволимо цифри та "+"
    raw = raw.strip()
    cleaned = []
    for ch in raw:
        if ch.isdigit() or ch == "+":
            cleaned.append(ch)
    return "".join(cleaned)


@router.message(LeadForm.phone)
async def process_phone(message: Message, state: FSMContext):
    phone_raw = message.text or ""
    phone = _normalize_phone(phone_raw)

    # Дуже базова перевірка: довжина та наявність цифр
    digits = [c for c in phone if c.isdigit()]
    if len(digits) < 10:
        await message.answer("Схоже, номер некоректний. Вкажіть телефон ще раз (мінімум 10 цифр):")
        return

    await state.update_data(phone=phone)
    await state.set_state(LeadForm.comment)
    await message.answer("Додайте коментар до заявки (або напишіть: Без коментаря):")


@router.message(LeadForm.comment)
async def process_comment(message: Message, state: FSMContext):
    comment = (message.text or "").strip()
    if not comment:
        comment = "Без коментаря"

    data = await state.get_data()
    name = data.get("name", "—")
    phone = data.get("phone", "—")

    await state.clear()

    await message.answer(
        "Дякую! ✅ Заявку сформовано.\n\n"
        f"👤 Ім’я: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📝 Коментар: {comment}\n\n"
        "Ми зв’яжемося з вами найближчим часом.",
        reply_markup=main_kb
    )