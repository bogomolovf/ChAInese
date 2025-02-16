from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command,  StateFilter
from aiogram.types import Message
from aiogram import Router, types, F
from psycopg2 import sql
import psycopg2
import utils.keyboards
import logging
import pypinyin
from deep_translator import GoogleTranslator
from database.db import DATABASE_URL


class StateFilter(StatesGroup):
    OPTION = State()
    NEW_WORD = State()
    DELETE_WORD = State()


router = Router()

logger = logging.getLogger(__name__)

@router.message(lambda msg: msg.text == "Add flashcard", StateFilter.OPTION)
async def add_flashcard_handler(message: types.Message, state: FSMContext):
    """
    Prompts the user to add a new flashcard to the selected list.
    """
    data = await state.get_data()
    selected_list = data.get("selected_list")

    if not selected_list:
        await message.reply("Please choose a list first.", reply_markup=utils.keyboards.reply_keyboard)
        return

    await message.reply("Write the new word in Chinese:")
    await state.set_state(StateFilter.NEW_WORD)


@router.message(StateFilter.NEW_WORD)
async def process_flashcard_input(message: types.Message, state: FSMContext):
    """
    Processes the input for adding a new flashcard to the selected list.
    """
    data = await state.get_data()
    selected_list = data.get("selected_list")

    if not selected_list:
        await message.reply("Please choose a list first.")
        return


    chinese_word = message.text
    context = GoogleTranslator(source='zh-CN', target='ru').translate(chinese_word)

    if not chinese_word or not context:
        await message.reply("Both the word and translation must be provided. Please try again.")
        return

    # Generate pinyin with tones
    pinyin = ' '.join(pypinyin.lazy_pinyin(chinese_word, style=pypinyin.Style.TONE))

    try:
        # Add flashcard to the selected list
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL(
                """
                INSERT INTO router (user_id, word, pinyin, context, list_id)
                VALUES (%s, %s, %s, %s, %s)
                """
            ),
            (message.from_user.id, chinese_word, pinyin, context, selected_list)
        )
        conn.commit()
        cur.close()
        conn.close()

        await message.reply(f"Flashcard added successfully:\nWord: {chinese_word}\nPinyin: {pinyin}\nTranslation: {context}")
    except Exception as e:
        await message.reply(f"An error occurred while adding the flashcard: {e}")

    # Return to the flashcard menu
    await state.set_state(StateFilter.OPTION)






@router.message(lambda msg: msg.text == "See router", StateFilter.OPTION)
async def see_flashcards_handler(message: types.Message, state: FSMContext):
    """
    Handles the 'See router' button to display router from the selected list.
    """
    try:
        # Get the selected list from the state
        user_data = await state.get_data()
        selected_list = user_data.get("selected_list")

        if not selected_list:
            await message.reply("You need to choose a list first.")
            return

        # Fetch router from the database for the selected list
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT word, pinyin, context FROM router WHERE user_id = %s AND list_id = %s"),
            (message.from_user.id, selected_list)
        )
        router = cur.fetchall()
        cur.close()
        conn.close()

        if router:
            # Display router with Chinese characters, Pinyin, and translation
            response = f"Flashcards from the selected list:\n"
            for idx, (word, pinyin, translation) in enumerate(router, start=1):
                response += f"{idx}. {word} ({pinyin}): {translation}\n"
            await message.reply(response)
        else:
            await message.reply("This list has no router.")
    except Exception as e:
        await message.reply(f"An error occurred while fetching router: {e}")


@router.message(lambda msg: msg.text == "Delete flashcard", StateFilter.OPTION)
async def delete_flashcard_handler(message: types.Message, state: FSMContext):
    """
    Handles the 'Delete flashcard' button to prompt the user for a word to delete.
    """
    await message.reply("Write the word of the flashcard you want to delete:")
    await state.set_state(StateFilter.DELETE_WORD)


@router.message(StateFilter.DELETE_WORD)
async def process_delete_flashcard(message: types.Message, state: FSMContext):
    """
    Processes the deletion of a flashcard by word.
    """
    word_to_delete = message.text.strip()

    try:
        # Delete flashcard from the database
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL(
                "DELETE FROM router WHERE user_id = %s AND word = %s RETURNING word"
            ),
            (message.from_user.id, word_to_delete)
        )
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if deleted:
            await message.reply(f"Flashcard '{word_to_delete}' has been deleted.", reply_markup=utils.keyboards.reply_keyboard)
        else:
            await message.reply(f"No flashcard found with the word '{word_to_delete}'.", reply_markup=utils.keyboards.reply_keyboard)
    except Exception as e:
        await message.reply(f"An error occurred while deleting the flashcard: {e}", reply_markup=utils.keyboards.reply_keyboard)

    # Reset state back to main flashcard menu
    await state.set_state(StateFilter.OPTION)


@router.message(lambda msg: msg.text == "Review router", StateFilter.OPTION)
async def review_flashcards_handler(message: types.Message, state: FSMContext):
    """
    Handles the 'Review router' button by starting a review of router from the selected list.
    """
    data = await state.get_data()
    selected_list = data.get("selected_list")

    if not selected_list:
        await message.reply("Please choose a list first.")
        return

    try:
        # Fetch router from the selected list
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT word, context FROM router WHERE user_id = %s AND list_id = %s"),
            (message.from_user.id, selected_list)
        )
        router = cur.fetchall()
        cur.close()
        conn.close()

        if router:
            # Store router in the state and start reviewing
            await state.update_data(router=router, current_index=0)
            await show_next_flashcard(message, state)
        else:
            await message.reply("This list has no router to review.")
    except Exception as e:
        await message.reply(f"An error occurred while fetching router: {e}")

async def show_next_flashcard(message: types.Message, state: FSMContext):
    """
    Shows the next flashcard to the user.
    """
    data = await state.get_data()
    router = data.get("router", [])
    current_index = data.get("current_index", 0)

    if current_index < len(router):
        word, _ = router[current_index]
        await message.answer(f"Word: {word}\nTry to remember its context. When you're ready, type 'show'.")
    else:
        await message.reply("You have reviewed all router!")
        await state.update_data(router=None, current_index=None)  # Clear review data


@router.message(lambda msg: msg.text.lower() == "show", StateFilter.OPTION)
async def show_flashcard_context(message: types.Message, state: FSMContext):
    """
    Shows the context of the currently reviewed flashcard and proceeds to the next one.
    """
    data = await state.get_data()
    router = data.get("router", [])
    current_index = data.get("current_index", 0)

    if current_index < len(router):
        word, context = router[current_index]
        await message.reply(f"Word: {word}\nContext: {context}")
        
        # Move to the next flashcard
        current_index += 1
        await state.update_data(current_index=current_index)
        await show_next_flashcard(message, state)
    else:
        await message.reply("No more router to review.")
        await state.update_data(router=None, current_index=None)  # Clear review data
