from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from common.database import Tutor, get_session
from tutor_bot.keyboards import get_start_keyboard, get_main_menu_keyboard, DAY_NAMES

async def cmd_start(message: types.Message):
    async for session in get_session():
        # Ищем репетитора по telegram_id
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == message.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if tutor:  # Если нашли репетитора в базе
            # Форматируем список предметов с типами
           
            await message.answer(
                "🎯 Используйте меню для управления профилем:",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            return
    
    # Если пользователь не найден в базе, показываем стандартное приветствие
    welcome_text = (
        "👋 Добро пожаловать в систему регистрации репетиторов!\n\n"
        "🎓 Я помогу вам создать профиль репетитора.\n"
        "📝 Нажмите кнопку ниже, чтобы начать регистрацию."
    )
    await message.answer(welcome_text, reply_markup=get_start_keyboard())

def register_common_handlers(dp):
    dp.message.register(cmd_start, Command("start")) 