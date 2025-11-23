import asyncio
import logging
import sys

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app import log, router
from config import BOT_TOKEN, BACKEND_URL

#  Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher(storage=MemoryStorage())


async def main():
    dp.include_routers(router)

    try:
        log.info("Стартуем polling… BACKEND_URL=%s | PY=%s", BACKEND_URL, sys.executable)
        await dp.start_polling(bot, skip_updates=True)
        me = await bot.get_me()
        log.info("Бот запущен: %s (@%s) | BACKEND_URL=%s | PY=%s", me.first_name, me.username, BACKEND_URL, sys.executable)
    except Exception as e:
        log.error("❗ Не удалось авторизоваться ботом. Проверь BOT_TOKEN. %s", e)
        print("\n❗ BOT_TOKEN неверен/отозван или нет сети. Проверь токен в bot/.env.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(main())