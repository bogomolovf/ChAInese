from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import Bot


DATABASE_URL = "postgresql://postgres.uilrtenermvclsnjlcym:goodgame2254FF@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
BOT_TOKEN = '7379769326:AAFpOSucF2-PEqC5s8i5mNBa8pGjVzqJycU'
bot = Bot(token=BOT_TOKEN)




main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изучение китайского с нуля")],
        [KeyboardButton(text="Подготовка к HSK")],
        [KeyboardButton(text="Распознать иероглиф")],
        [KeyboardButton(text="Карточки")],
        [KeyboardButton(text="Мой профиль")],
    ],
    resize_keyboard=True
)

reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add flashcard"), KeyboardButton(text="See flashcards")],
        [KeyboardButton(text="Delete flashcard"), KeyboardButton(text="Review flashcards")], 
        [KeyboardButton(text="Learn flashcards"), KeyboardButton(text="Done")],
    ],
    resize_keyboard=True
)

first_markup = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Create list")],
        [KeyboardButton(text="Choose list")],
        [KeyboardButton(text="Delete list")],
    ],
    resize_keyboard=True
)