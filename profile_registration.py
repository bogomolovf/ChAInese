from aiogram.fsm.state import StatesGroup, State
import psycopg2
import MAINdata
import logging
from aiogram import Router, types
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

prr = Router()

class RegistrationStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_email = State()



def save_user(user_id, nickname, email):
    try:
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (user_id, nickname, email)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user_id, nickname, email),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logging.error(f"Error saving user: {e}")


def get_user_profile(user_id):
    try:
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
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
 
def is_user_registered(user_id):
    try:
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()

        # Check if the user exists in the database
        cur.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = %s)", (user_id,))
        registered = cur.fetchone()[0]

        cur.close()
        conn.close()

        return registered
    except Exception as e:
        logging.error(f"Error checking user registration: {e}")

@prr.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        # Check if the user is already registered
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            # If registered, show the main menu
            await message.answer(
                "Добро пожаловать обратно в бота для изучения китайского языка! Выберите, с чего начать:",
                reply_markup=MAINdata.main_menu,
            )
        else:
            # If not registered, start the registration process
            await state.set_state(RegistrationStates.waiting_for_nickname)
            await message.answer("Добро пожаловать! Давайте начнем с регистрации. Пожалуйста, введите ваш никнейм:")
    except Exception as e:
        await message.answer("Произошла ошибка. Попробуйте снова позже.")
        logging.error(f"Error in start_handler: {e}")


@prr.message(RegistrationStates.waiting_for_nickname)
async def nickname_handler(message: Message, state: FSMContext):
    nickname = message.text.strip()
    if not nickname:
        await message.reply("Никнейм не может быть пустым. Пожалуйста, введите ваш никнейм:")
        return

    await state.update_data(nickname=nickname)
    await state.set_state(RegistrationStates.waiting_for_email)
    await message.reply("Отлично! Теперь введите ваш адрес электронной почты:")


# Email handler
@prr.message(RegistrationStates.waiting_for_email)
async def email_handler(message: Message, state: FSMContext):
    email = message.text.strip()
    if "@" not in email or "." not in email:
        await message.reply("Пожалуйста, введите действительный адрес электронной почты:")
        return

    data = await state.get_data()
    nickname = data.get("nickname")
    user_id = message.from_user.id

    # Save user to the database
    save_user(user_id, nickname, email)
    await message.reply(
        "Регистрация завершена! Добро пожаловать в бота для изучения китайского языка.",
        reply_markup=MAINdata.main_menu,
    )

    # Clear the state
    await state.clear()