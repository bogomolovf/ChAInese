import os
import logging
from random import sample
import psycopg2
from psycopg2 import sql
from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

logger = logging.getLogger(__name__)

# Database connection settings
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5432/flashcardb"
)

# FSM States
class FlashcardStates(StatesGroup):
    OPTION = State()
    NEW_WORD = State()
    EDIT_WORD = State()

# Keyboard for main menu
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add flashcard"), KeyboardButton(text="See flashcards")],
        [KeyboardButton(text="Delete flashcard"), KeyboardButton(text="Review flashcards")],
        [KeyboardButton(text="Done")],
    ],
    resize_keyboard=True
)

# Initialize router
flashcard_router = Router()

def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        raise

def init_db():
    try:
        conn = connect_db()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS flashcards (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                word TEXT NOT NULL,
                context TEXT NOT NULL
            );
            """
        )

        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        logger.error(f"Error initializing the database: {e}")

@flashcard_router.message(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    reply_text = "Hi! I'm the flashcard bot."

    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT 1 FROM flashcards WHERE user_id = %s LIMIT 1;"),
            (message.from_user.id,)
        )
        if cur.fetchone():
            reply_text += " You already have some flashcards saved."
        reply_text += " Do you want to add new words?"
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error fetching user data: {e}")

    await message.reply(reply_text, reply_markup=reply_keyboard)
    await state.set_state(FlashcardStates.OPTION)

@flashcard_router.message(lambda msg: msg.text == "Add flashcard", state=FlashcardStates.OPTION)
async def ask_flashcard(message: types.Message, state: FSMContext):
    await message.reply("Write the new word and its context in this format: word=example sentence")
    await state.set_state(FlashcardStates.NEW_WORD)

@flashcard_router.message(state=FlashcardStates.NEW_WORD)
async def save_info(message: types.Message, state: FSMContext):
    text = message.text.split("=")
    if len(text) != 2:
        await message.reply("Please use the correct format: word=example sentence")
        await state.set_state(FlashcardStates.OPTION)
        return

    new_word, word_context = text[0].strip(), text[1].strip()

    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute(
            sql.SQL(
                """
                INSERT INTO flashcards (user_id, word, context)
                VALUES (%s, %s, %s)
                """
            ),
            (message.from_user.id, new_word, word_context)
        )
        conn.commit()
        cur.close()
        conn.close()
        await message.reply(f"New word added: '{new_word}' with context: '{word_context}'", reply_markup=reply_keyboard)
    except Exception as e:
        logger.error(f"Error saving flashcard: {e}")

    await state.set_state(FlashcardStates.OPTION)

@flashcard_router.message(lambda msg: msg.text == "See flashcards", state=FlashcardStates.OPTION)
async def see_flashcards(message: types.Message):
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT word, context FROM flashcards WHERE user_id = %s;"),
            (message.from_user.id,)
        )
        flashcards = cur.fetchall()
        cur.close()
        conn.close()

        if not flashcards:
            await message.reply("You have no flashcards saved.")
            return

        reply_text = "Your flashcards:\n"
        for i, (word, context) in enumerate(flashcards, start=1):
            reply_text += f"{i}. {word}: {context}\n"

        await message.reply(reply_text)
    except Exception as e:
        logger.error(f"Error fetching flashcards: {e}")

@flashcard_router.message(lambda msg: msg.text == "Delete flashcard", state=FlashcardStates.OPTION)
async def ask_delete_flashcard(message: types.Message):
    await message.reply("Write the word you want to delete from the flashcard system.")
    await FlashcardStates.EDIT_WORD.set()

@flashcard_router.message(state=FlashcardStates.EDIT_WORD)
async def delete_flashcard(message: types.Message, state: FSMContext):
    word = message.text.strip()

    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute(
            sql.SQL("DELETE FROM flashcards WHERE user_id = %s AND word = %s RETURNING id;"),
            (message.from_user.id, word)
        )
        if cur.rowcount > 0:
            conn.commit()
            await message.reply(f"The word '{word}' was deleted.", reply_markup=reply_keyboard)
        else:
            await message.reply(f"No flashcard found with the word '{word}'.", reply_markup=reply_keyboard)
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error deleting flashcard: {e}")

    await state.set_state(FlashcardStates.OPTION)

@flashcard_router.message(lambda msg: msg.text == "Review flashcards", state=FlashcardStates.OPTION)
async def review_flashcards(message: types.Message, state: FSMContext):
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT word, context FROM flashcards WHERE user_id = %s;"),
            (message.from_user.id,)
        )
        flashcards = cur.fetchall()
        cur.close()
        conn.close()

        if not flashcards:
            await message.reply("You have no flashcards to review.")
            return

        flashcard = sample(flashcards, 1)[0]
        await message.reply(f"Word: {flashcard[0]}\nTry to remember its context. When you're ready, type 'show'.")
        await state.update_data(reviewing=flashcard)
    except Exception as e:
        logger.error(f"Error fetching flashcards for review: {e}")

@flashcard_router.message(lambda msg: msg.text.lower() == "show", state=FlashcardStates.OPTION)
async def show_review_context(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reviewing_flashcard = data.get('reviewing')

    if not reviewing_flashcard:
        await message.reply("No word is being reviewed right now.")
        return

    await message.reply(f"Word: {reviewing_flashcard[0]}\nContext: {reviewing_flashcard[1]}")
    await state.update_data(reviewing=None)

@flashcard_router.message(lambda msg: msg.text == "Done", state=FlashcardStates.OPTION)
async def done(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply("Goodbye! See you next time.")

# Initialize the database
init_db()

