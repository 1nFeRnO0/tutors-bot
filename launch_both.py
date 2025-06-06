import asyncio
from parent_bot.main import main as parent_main
from tutor_bot.main import main as tutor_main

async def run_both():
    # Запуск обоих ботов параллельно
    await asyncio.gather(
        parent_main(),
        tutor_main()
    )

if __name__ == "__main__":
    asyncio.run(run_both())
