from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import re

from parent_bot.keyboards import get_registration_form_keyboard, get_registration_menu_keyboard, get_main_menu_keyboard
from common.database import Parent, get_session

router = Router()

class ParentRegistration(StatesGroup):
    """Состояния регистрации родителя"""
    waiting_for_name_surname = State()
    waiting_for_name_input = State()
    waiting_for_surname_input = State()
    waiting_for_patronymic_input = State()
    waiting_for_phone = State()

def validate_phone(phone: str) -> bool:
    """Проверяет корректность номера телефона"""
    # Удаляем все не цифры из номера
    cleaned_phone = re.sub(r'\D', '', phone)
    # Проверяем что длина 11 цифр и начинается с 7 или 8
    return len(cleaned_phone) == 11 and cleaned_phone[0] in ('7', '8')

def format_phone(phone: str) -> str:
    """Форматирует номер телефона в красивый вид"""
    cleaned_phone = re.sub(r'\D', '', phone)
    if cleaned_phone[0] == '8':
        cleaned_phone = '7' + cleaned_phone[1:]
    return f"+{cleaned_phone[0]} ({cleaned_phone[1:4]}) {cleaned_phone[4:7]}-{cleaned_phone[7:9]}-{cleaned_phone[9:11]}"

async def process_start_registration(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard()
    )
    await state.set_state(ParentRegistration.waiting_for_name_surname)

async def process_edit_name(callback_query: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == ParentRegistration.waiting_for_name_surname.state:
        await callback_query.message.edit_text("Как вас зовут?")
        await state.set_state(ParentRegistration.waiting_for_name_input)

async def process_edit_surname(callback_query: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == ParentRegistration.waiting_for_name_surname.state:
        await callback_query.message.edit_text("Какая у вас фамилия?")
        await state.set_state(ParentRegistration.waiting_for_surname_input)

async def process_edit_patronymic(callback_query: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == ParentRegistration.waiting_for_name_surname.state:
        await callback_query.message.edit_text(
            "Какое у вас отчество? (Если отчества нет, просто нажмите 'Продолжить')",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Продолжить без отчества", callback_data="skip_patronymic")]
            ])
        )
        await state.set_state(ParentRegistration.waiting_for_patronymic_input)

async def process_name_input(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(name=message.text)
    await message.answer(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard(name=message.text, surname=data.get("surname", ""))
    )
    await state.set_state(ParentRegistration.waiting_for_name_surname)

async def process_surname_input(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(surname=message.text)
    await message.answer(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard(name=data.get("name", ""), surname=message.text)
    )
    await state.set_state(ParentRegistration.waiting_for_name_surname)

async def process_patronymic_input(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(patronymic=message.text)
    await message.answer(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard(
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            patronymic=message.text
        )
    )
    await state.set_state(ParentRegistration.waiting_for_name_surname)

async def skip_patronymic(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback_query.message.edit_text(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard(
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            patronymic=""
        )
    )
    await state.set_state(ParentRegistration.waiting_for_name_surname)

async def process_finish_name_surname(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("name") or not data.get("surname"):
        await callback_query.answer("Пожалуйста, заполните имя и фамилию!")
        return
    
    await callback_query.message.edit_text(
        "📱 Введите ваш номер телефона в любом формате:\n"
        "Например: +79991234567 или 89991234567"
    )
    await state.set_state(ParentRegistration.waiting_for_phone)

async def process_phone_input(message: Message, state: FSMContext):
    if not validate_phone(message.text):
        await message.answer(
            "❌ Неверный формат номера телефона!\n"
            "Введите номер в формате: +79991234567 или 89991234567"
        )
        return

    data = await state.get_data()
    formatted_phone = format_phone(message.text)
    
    # Создаем запись в базе данных
    async for session in get_session():
        parent = Parent(
            telegram_id=message.from_user.id,
            name=data["name"],
            surname=data["surname"],
            patronymic=data.get("patronymic"),
            phone=formatted_phone
        )
        session.add(parent)
        await session.commit()
    
    await message.answer(
        "🎉 Регистрация успешно завершена!\n\n"
        "Чтобы записаться ребенка к репетитору:\n"
        "1. Добавьте данные ребенка в настройках профиля\n"
        "2. Найдите нужного репетитора\n"
        "3. Запишитесь на занятие\n\n"
        "Используйте меню для управления профилем.",
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()

def register_registration_handlers(dp):
    dp.callback_query.register(process_start_registration, lambda c: c.data == "start_registration")
    dp.callback_query.register(process_edit_name, lambda c: c.data == "edit_name")
    dp.callback_query.register(process_edit_surname, lambda c: c.data == "edit_surname")
    dp.callback_query.register(process_edit_patronymic, lambda c: c.data == "edit_patronymic")
    dp.message.register(process_name_input, ParentRegistration.waiting_for_name_input)
    dp.message.register(process_surname_input, ParentRegistration.waiting_for_surname_input)
    dp.message.register(process_patronymic_input, ParentRegistration.waiting_for_patronymic_input)
    dp.message.register(process_phone_input, ParentRegistration.waiting_for_phone)
    dp.callback_query.register(process_finish_name_surname, lambda c: c.data == "finish_name_surname")
    dp.callback_query.register(skip_patronymic, lambda c: c.data == "skip_patronymic") 