import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from common.config import TUTOR_BOT_TOKEN, PARENT_BOT_TOKEN
from common.database import init_db
from tutor_bot.handlers.common import register_common_handlers
from tutor_bot.handlers.registration import register_registration_handlers
from tutor_bot.handlers.profile import register_profile_handlers
from tutor_bot.handlers.booking import register_booking_handlers
from tutor_bot.handlers.students import register_students_handlers

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TUTOR_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def main():
    # Инициализация базы данных
    await init_db()
    
    # Регистрация обработчиков
    register_common_handlers(dp)
    register_registration_handlers(dp)
    register_profile_handlers(dp)
    register_booking_handlers(dp)
    register_students_handlers(dp)
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())