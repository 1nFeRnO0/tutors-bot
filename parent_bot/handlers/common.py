from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from common.database import Parent, get_session
from parent_bot.keyboards import get_start_keyboard, get_main_menu_keyboard

async def cmd_start(message: types.Message):
    async for session in get_session():
        # Ищем родителя по telegram_id
        parent = await session.execute(
            select(Parent).where(Parent.telegram_id == message.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if parent:  # Если нашли родителя в базе
            await message.answer(
                "👋 Добро пожаловать в систему записи к репетиторам!\n"
                "Используйте меню для управления профилем:",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            return
    
    # Если пользователь не найден в базе, показываем стандартное приветствие
    welcome_text = (
        "👋 Добро пожаловать в систему записи к репетиторам!\n\n"
        "👨‍👩‍👧‍👦 Я помогу вам найти подходящего репетитора для вашего ребенка.\n"
        "📝 Нажмите кнопку ниже, чтобы начать регистрацию."
    )
    await message.answer(welcome_text, reply_markup=get_start_keyboard())

def register_common_handlers(dp):
    dp.message.register(cmd_start, Command("start")) 