from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import re

from common.database import Parent, get_session
from parent_bot.keyboards import get_main_menu_keyboard
from parent_bot.handlers.registration import validate_phone, format_phone

class ProfileEditing(StatesGroup):
    editing_name = State()
    editing_surname = State()
    editing_patronymic = State()
    editing_phone = State()

def get_profile_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="👤 Изменить ФИО", callback_data="edit_profile_name")],
        [InlineKeyboardButton(text="📱 Изменить телефон", callback_data="edit_profile_phone")],
        [InlineKeyboardButton(text="◀️ Вернуться в главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_edit_keyboard(name: str = "", surname: str = "", patronymic: str = "") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="👤 Изменить имя", callback_data="profile_edit_name"),
            InlineKeyboardButton(text=name or "❌ Не указано", callback_data="profile_edit_name")
        ],
        [
            InlineKeyboardButton(text="👤 Изменить фамилию", callback_data="profile_edit_surname"),
            InlineKeyboardButton(text=surname or "❌ Не указано", callback_data="profile_edit_surname")
        ],
        [
            InlineKeyboardButton(text="👤 Изменить отчество", callback_data="profile_edit_patronymic"),
            InlineKeyboardButton(text=patronymic or "❌ Не указано", callback_data="profile_edit_patronymic")
        ],
        [InlineKeyboardButton(text="💾 Сохранить изменения", callback_data="profile_save_name_surname")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def show_profile(callback_query: types.CallbackQuery):
    async for session in get_session():
        parent = await session.execute(
            select(Parent).where(Parent.telegram_id == callback_query.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent:
            await callback_query.answer("❌ Профиль не найден!")
            return
        
        # Форматируем полное имя с отчеством (если есть)
        full_name = f"{parent.name} {parent.surname}"
        if parent.patronymic:
            full_name = f"{parent.name} {parent.patronymic} {parent.surname}"
        
        profile_text = (
            f"👤 <b>Профиль родителя</b>\n\n"
            f"👤 ФИО: {full_name}\n"
            f"📱 Телефон: {parent.phone or 'Не указан'}\n"
        )
        
        await callback_query.message.edit_text(
            profile_text,
            reply_markup=get_profile_menu_keyboard(),
            parse_mode="HTML"
        )

async def edit_profile_name(callback_query: types.CallbackQuery, state: FSMContext):
    async for session in get_session():
        parent = await session.execute(
            select(Parent).where(Parent.telegram_id == callback_query.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        if parent:
            await state.update_data(
                name=parent.name,
                surname=parent.surname,
                patronymic=parent.patronymic
            )
            await callback_query.message.edit_text(
                "Редактирование профиля:",
                reply_markup=get_profile_edit_keyboard(
                    name=parent.name,
                    surname=parent.surname,
                    patronymic=parent.patronymic
                )
            )
            await state.set_state(ProfileEditing.editing_name)

async def process_edit_name(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    await callback_query.message.edit_text("Введите новое имя:")
    await state.set_state(ProfileEditing.editing_name)

async def process_edit_surname(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    await callback_query.message.edit_text("Введите новую фамилию:")
    await state.set_state(ProfileEditing.editing_surname)

async def process_edit_patronymic(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    await callback_query.message.edit_text(
        "Введите новое отчество (или оставьте пустым):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="profile_cancel_patronymic")]
        ])
    )
    await state.set_state(ProfileEditing.editing_patronymic)

async def process_name_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    data = await state.get_data()
    await state.update_data(name=message.text)
    await message.answer(
        "Редактирование профиля:",
        reply_markup=get_profile_edit_keyboard(
            name=message.text,
            surname=data.get("surname", ""),
            patronymic=data.get("patronymic", "")
        )
    )
    await state.set_state(ProfileEditing.editing_name)

async def process_surname_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_surname.state:
        return
        
    data = await state.get_data()
    await state.update_data(surname=message.text)
    await message.answer(
        "Редактирование профиля:",
        reply_markup=get_profile_edit_keyboard(
            name=data.get("name", ""),
            surname=message.text,
            patronymic=data.get("patronymic", "")
        )
    )
    await state.set_state(ProfileEditing.editing_name)

async def process_patronymic_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_patronymic.state:
        return
        
    data = await state.get_data()
    await state.update_data(patronymic=message.text)
    await message.answer(
        "Редактирование профиля:",
        reply_markup=get_profile_edit_keyboard(
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            patronymic=message.text
        )
    )
    await state.set_state(ProfileEditing.editing_name)

async def cancel_patronymic_edit(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback_query.message.edit_text(
        "Редактирование профиля:",
        reply_markup=get_profile_edit_keyboard(
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            patronymic=data.get("patronymic", "")
        )
    )
    await state.set_state(ProfileEditing.editing_name)

async def save_profile_name_surname(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    data = await state.get_data()
    if not data.get("name") or not data.get("surname"):
        await callback_query.answer("Пожалуйста, заполните имя и фамилию!")
        return
    
    async for session in get_session():
        parent = await session.execute(
            select(Parent).where(Parent.telegram_id == callback_query.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        if parent:
            parent.name = data["name"]
            parent.surname = data["surname"]
            parent.patronymic = data.get("patronymic")
            await session.commit()
    
    await callback_query.message.edit_text(
        "✅ ФИО успешно обновлены!",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

async def back_to_main(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🎯 Используйте меню для управления профилем:",
        reply_markup=get_main_menu_keyboard()
    )

async def edit_profile_phone(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "📱 Введите новый номер телефона в любом формате:\n"
        "Например: +79991234567 или 89991234567"
    )
    await state.set_state(ProfileEditing.editing_phone)

async def process_phone_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_phone.state:
        return

    if not validate_phone(message.text):
        await message.answer(
            "❌ Неверный формат номера телефона!\n"
            "Введите номер в формате: +79991234567 или 89991234567",
            reply_markup=get_profile_menu_keyboard()
        )
        return

    formatted_phone = format_phone(message.text)
    
    async for session in get_session():
        parent = await session.execute(
            select(Parent).where(Parent.telegram_id == message.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        if parent:
            parent.phone = formatted_phone
            await session.commit()
    
    await message.answer(
        "✅ Номер телефона успешно обновлен!",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

def register_profile_handlers(dp):
    # Показ профиля
    dp.callback_query.register(show_profile, lambda c: c.data == "profile")
    
    # Редактирование ФИО
    dp.callback_query.register(edit_profile_name, lambda c: c.data == "edit_profile_name")
    dp.callback_query.register(process_edit_name, lambda c: c.data == "profile_edit_name")
    dp.callback_query.register(process_edit_surname, lambda c: c.data == "profile_edit_surname")
    dp.callback_query.register(process_edit_patronymic, lambda c: c.data == "profile_edit_patronymic")
    dp.message.register(process_name_input, lambda m: True, ProfileEditing.editing_name)
    dp.message.register(process_surname_input, lambda m: True, ProfileEditing.editing_surname)
    dp.message.register(process_patronymic_input, lambda m: True, ProfileEditing.editing_patronymic)
    dp.callback_query.register(cancel_patronymic_edit, lambda c: c.data == "profile_cancel_patronymic")
    dp.callback_query.register(save_profile_name_surname, lambda c: c.data == "profile_save_name_surname")
    
    # Редактирование телефона
    dp.callback_query.register(edit_profile_phone, lambda c: c.data == "edit_profile_phone")
    dp.message.register(process_phone_input, lambda m: True, ProfileEditing.editing_phone)
    
    # Возврат в главное меню
    dp.callback_query.register(back_to_main, lambda c: c.data == "back_to_main") 