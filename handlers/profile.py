from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from database.db import db_execute, DATABASE_URL
from utils.keyboards import main_menu
import logging
import psycopg2
from aiogram.filters import Command

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    try:
        # Check if the user is already registered
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            # If registered, show the main menu
            await message.answer(
                "Добро пожаловать обратно в бота для изучения китайского языка! Выберите, с чего начать:",
                reply_markup=main_menu,
            )
        else:
            # If not registered, start the registration process
            await state.set_state("waiting_for_nickname")
            await message.answer("Добро пожаловать! Давайте начнем с регистрации. Пожалуйста, введите ваш никнейм:")
    except Exception as e:
        await message.answer("Произошла ошибка. Попробуйте снова позже.")
        logging.error(f"Error in start_handler: {e}")



@router.message(StateFilter("waiting_for_nickname"))
async def nickname_handler(message: types.Message, state: FSMContext):
    nickname = message.text.strip()
    await state.update_data(nickname=nickname)
    await state.set_state("waiting_for_email")
    await message.answer("📧 Введите ваш e-mail:")

@router.message(StateFilter("waiting_for_email"))
async def email_handler(message: types.Message, state: FSMContext):
    email = message.text.strip()
    data = await state.get_data()
    nickname = data["nickname"]
    user_id = message.from_user.id

    await db_execute("INSERT INTO users (user_id, nickname, email) VALUES (%s, %s, %s)", (user_id, nickname, email))
    await message.answer("✅ Регистрация завершена!", reply_markup=main_menu)
    await state.clear()

### ✅ Просмотр профиля
@router.message(F.text == "Мой профиль")
async def profile_handler(message: types.Message):

    user_id = message.from_user.id

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Fetch user details
        cur.execute("SELECT nickname FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()

        cur.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
        email = cur.fetchone()
        # Fetch user flashcards
        cur.execute("SELECT word, context FROM flashcards WHERE user_id = %s", (user_id,))
        flashcards = cur.fetchall()

        cur.close()
        conn.close()

        return user, *email, flashcards
    except Exception as e:
        logging.error(f"Error fetching user profile: {e}")
        return None, None, []
