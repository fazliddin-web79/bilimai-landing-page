import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import Config
from bot.database import Database
from bot.handlers import routers


async def main() -> None:
    config = Config.from_env()
    database = Database(config.database_path)
    await database.initialize()

    bot = Bot(token=config.telegram_bot_token)
    dispatcher = Dispatcher()
    for router in routers:
        dispatcher.include_router(router)

    await dispatcher.start_polling(
        bot,
        database=database,
        config=config,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(main())
