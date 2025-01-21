import os
import logging
from random import sample
from pymongo import MongoClient
from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

logger = logging.getLogger(__name__)

# Вместо MONGODB_URL поставь url на нашу бд куда он будет сохранять карточки со словами пользователей
MONGODB_URL = os.getenv('MONGODB_URL')
if not MONGODB_URL:
    raise ValueError("No MONGO_URL found in the environment variables")

client = MongoClient(MONGODB_URL)
db = client.flashcardb
coll = db.flashcardb

# Состояния FSM
class FlashcardStates(StatesGroup):
    OPTION = State()
    NEW_WORD = State()
    EDIT_WORD = State()

# Клавиатура для работы с карточками
reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add flashcard"), KeyboardButton(text="See flashcards")],
        [KeyboardButton(text="Delete flashcard"), KeyboardButton(text="Review flashcards")],
        [KeyboardButton(text="Done")],
    ],
    resize_keyboard=True
)

# Инициализация роутера
flashcard_router = Router()

@flashcard_router.message(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    reply_text = "Hi! I'm the flashcard bot."

    # Проверяем, есть ли данные пользователя
    user_data = coll.find_one({"user_id": message.from_user.id})
    if user_data and user_data.get('flashcards'):
        reply_text += " You already have some flashcards saved. Do you want to review them?"
    reply_text += " Do you want to add new words?"

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
    coll.update_one(
        {'user_id': message.from_user.id},
        {'$set': {f'flashcards.{new_word}': word_context}},
        upsert=True
    )

    await message.reply(f"New word added: '{new_word}' with context: '{word_context}'", reply_markup=reply_keyboard)
    await state.set_state(FlashcardStates.OPTION)

@flashcard_router.message(lambda msg: msg.text == "See flashcards", state=FlashcardStates.OPTION)
async def see_flashcards(message: types.Message):
    user_data = coll.find_one({"user_id": message.from_user.id})

    if not user_data or not user_data.get('flashcards'):
        await message.reply("You have no flashcards saved.")
        return

    flashcards = user_data['flashcards']
    reply_text = "Your flashcards:\n"
    for i, (word, context) in enumerate(flashcards.items(), start=1):
        reply_text += f"{i}. {word}: {context}\n"

    await message.reply(reply_text)

@flashcard_router.message(lambda msg: msg.text == "Delete flashcard", state=FlashcardStates.OPTION)
async def ask_delete_flashcard(message: types.Message):
    await message.reply("Write the word you want to delete from the flashcard system.")
    await FlashcardStates.EDIT_WORD.set()

@flashcard_router.message(state=FlashcardStates.EDIT_WORD)
async def delete_flashcard(message: types.Message, state: FSMContext):
    word = message.text.strip()

    coll.update_one(
        {'user_id': message.from_user.id},
        {'$unset': {f'flashcards.{word}': ""}}
    )

    await message.reply(f"The word '{word}' was deleted.", reply_markup=reply_keyboard)
    await state.set_state(FlashcardStates.OPTION)

@flashcard_router.message(lambda msg: msg.text == "Review flashcards", state=FlashcardStates.OPTION)
async def review_flashcards(message: types.Message, state: FSMContext):
    user_data = coll.find_one({"user_id": message.from_user.id})

    if not user_data or not user_data.get('flashcards'):
        await message.reply("You have no flashcards to review.")
        return

    flashcards = user_data['flashcards']
    all_words = list(flashcards.keys())
    word = sample(all_words, 1)[0]

    await message.reply(f"Word: {word}\nTry to remember its context. When you're ready, type 'show'.")
    await state.update_data(reviewing=word)

@flashcard_router.message(lambda msg: msg.text.lower() == "show", state=FlashcardStates.OPTION)
async def show_review_context(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reviewing_word = data.get('reviewing')

    if not reviewing_word:
        await message.reply("No word is being reviewed right now.")
        return

    user_data = coll.find_one({"user_id": message.from_user.id})
    flashcards = user_data.get('flashcards', {})
    context = flashcards.get(reviewing_word, "No context available.")

    await message.reply(f"Word: {reviewing_word}\nContext: {context}")
    await state.update_data(reviewing=None)

@flashcard_router.message(lambda msg: msg.text == "Done", state=FlashcardStates.OPTION)
async def done(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply("Goodbye! See you next time.")
