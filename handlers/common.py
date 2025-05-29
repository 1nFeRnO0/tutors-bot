from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database import Tutor, get_session
from keyboards import get_start_keyboard, get_main_menu_keyboard, DAY_NAMES

async def cmd_start(message: types.Message):
    async for session in get_session():
        # Ищем репетитора по telegram_id
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == message.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if tutor:  # Если нашли репетитора в базе
            # Формируем текст профиля
            profile_text = (
                f"👤 <b>Профиль репетитора</b>\n\n"
                f"Имя: {tutor.name}\n"
                f"Фамилия: {tutor.surname}\n"
                f"Предметы: {', '.join(tutor.subjects)}\n\n"
                f"О себе:\n{tutor.description}\n\n"
                f"Расписание:\n"
            )
            
            # Добавляем информацию о расписании
            for day_code, day_name in DAY_NAMES.items():
                day_info = tutor.schedule.get(day_code, {})
                if day_info.get("active"):
                    profile_text += f"{day_name}: {day_info['start']} - {day_info['end']}\n"
            
            await message.answer(
                profile_text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            return
    
    # Если пользователь не найден в базе, показываем стандартное приветствие
    welcome_text = (
        "👋 Добро пожаловать в систему регистрации репетиторов!\n\n"
        "Я помогу вам создать профиль репетитора. "
        "Нажмите кнопку ниже, чтобы начать регистрацию."
    )
    await message.answer(welcome_text, reply_markup=get_start_keyboard())

def register_common_handlers(dp):
    dp.message.register(cmd_start, Command("start")) 