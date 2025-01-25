import psycopg2
from psycopg2 import sql
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from random import sample


fcr = Router()

DATABASE_URL = "postgresql://postgres.uilrtenermvclsnjlcym:goodgame2254FF@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

# Initialize database
def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS flashcards (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                context TEXT NOT NULL
            )
            """
        )
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")

# FSM states
class FlashcardStates(StatesGroup):
    OPTION = State()
    NEW_WORD = State()
    DELETE_WORD = State()

# Main menu keyboard
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add flashcard"), KeyboardButton(text="See flashcards")],
        [KeyboardButton(text="Delete flashcard"), KeyboardButton(text="Review flashcards")],
        [KeyboardButton(text="Done")],
    ],
    resize_keyboard=True
)

# Add a flashcard to the database
def add_flashcard_to_db(user_id, word, context):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL(
                """
                INSERT INTO flashcards (user_id, word, context)
                VALUES (%s, %s, %s)
                """
            ),
            (user_id, word, context)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error adding flashcard: {e}")

# View flashcards from the database


# Bot commands and handlers
@fcr.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await message.reply("Hi! I'm the flashcard bot. Use the menu below to manage your flashcards.", reply_markup=reply_keyboard)
    await state.set_state(FlashcardStates.OPTION)

@fcr.message(lambda msg: msg.text == "Add flashcard", state=FlashcardStates.OPTION)
async def ask_flashcard(message: types.Message, state: FSMContext):
    await message.reply("Write the new word and its context in this format: word=example sentence")
    await state.set_state(FlashcardStates.NEW_WORD)

@fcr.message(state=FlashcardStates.NEW_WORD)
async def save_flashcard(message: types.Message, state: FSMContext):
    text = message.text.split("=")
    if len(text) != 2:
        await message.reply("Please use the correct format: word=example sentence")
        await state.set_state(FlashcardStates.OPTION)
        return

    new_word, word_context = text[0].strip(), text[1].strip()
    add_flashcard_to_db(message.from_user.id, new_word, word_context)
    await message.reply(f"New word added: '{new_word}' with context: '{word_context}'", reply_markup=reply_keyboard)
    await state.set_state(FlashcardStates.OPTION)










