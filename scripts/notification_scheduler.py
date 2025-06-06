import asyncio
import logging
from datetime import datetime
import sys
import os

# Добавляем родительскую директорию в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.notifications import check_and_send_notifications
from common.database import init_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('notification_service.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Основная функция для запуска проверки уведомлений"""
    try:
        # Инициализируем базу данных
        await init_db()
        
        while True:
            try:
                logger.info("Checking for notifications...")
                await check_and_send_notifications()
                logger.info("Notification check completed")
            except Exception as e:
                logger.error(f"Error during notification check: {e}")
            
            # Ждем 5 минут перед следующей проверкой
            await asyncio.sleep(300)
    except KeyboardInterrupt:
        logger.info("Notification service stopped by user")
    except Exception as e:
        logger.error(f"Critical error in notification service: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nNotification service stopped") 