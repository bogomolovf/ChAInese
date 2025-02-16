from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
import logging
import asyncio

from handlers import lists, flashcards, learning, profile
from database.db import init_db

BOT_TOKEN = '7379769326:AAFpOSucF2-PEqC5s8i5mNBa8pGjVzqJycU'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)


async def main():
    """Запускает бота"""
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Инициализация БД
    await init_db()

    # Регистрация роутеров
    dp.include_router(lists.router)
    dp.include_router(profile.router)
    dp.include_router(flashcards.router)
    dp.include_router(learning.router)

    # Установка команд
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
    ])

    # Запуск
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())