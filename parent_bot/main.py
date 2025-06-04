import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from common.config import PARENT_BOT_TOKEN
from parent_bot.handlers.registration import register_registration_handlers
from parent_bot.handlers.common import register_common_handlers
from parent_bot.handlers.profile import register_profile_handlers
from parent_bot.handlers.children import register_children_handlers
from parent_bot.handlers.tutors import register_tutors_handlers
from parent_bot.handlers.booking import register_booking_handlers
from common.database import init_db

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=PARENT_BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

async def main():
    # Инициализация базы данных
    await init_db()
    
    # Регистрация обработчиков
    register_common_handlers(dp)
    register_registration_handlers(dp)
    register_profile_handlers(dp)
    register_children_handlers(dp)
    register_tutors_handlers(dp)
    register_booking_handlers(dp)
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 