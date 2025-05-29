import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers.common import register_common_handlers
from handlers.registration import register_registration_handlers
from handlers.profile import register_profile_handlers

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def main():
    # Инициализация базы данных
    await init_db()
    
    # Регистрация обработчиков
    register_common_handlers(dp)
    register_registration_handlers(dp)
    register_profile_handlers(dp)
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())