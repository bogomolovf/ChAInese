from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import Router
from aiogram import types
from psycopg2 import sql
import psycopg2
import MAINdata
import logging

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import pypinyin
from deep_translator import GoogleTranslator
import random
import datetime as dt
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

fcr = Router()

logger = logging.getLogger(__name__)



# Initialize database
def init_db():
    try:
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS flashcards (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                pinyin TEXT NOT NULL,
                context TEXT,
                list_id INTEGER NOT NULL
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
class StateFilter(StatesGroup):
    OPTION = State()
    NEW_WORD = State()
    DELETE_WORD = State()
    NEW_LIST = State()
    REVIEW_LIST = State()
    CHOOSE_LIST = State()
    DELETE_LIST = State()
    LEARN = State()
    INPUT_TRANSLATION = State()
    INPUT_HANZI = State()
    POLL_QUESTION = State()
    NEXT = State()




def create_flashcard_list(user_id, list_name):
    try:
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO lists (user_id, list_name)
            VALUES (%s, %s)
            ON CONFLICT (user_id, list_name) DO NOTHING
            """,
            (user_id, list_name)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error creating flashcard list: {e}")


def get_user_lists(user_id):
    try:
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, list_name FROM lists WHERE user_id = %s
            """,
            (user_id,)
        )
        lists = cur.fetchall()
        cur.close()
        conn.close()
        return lists
    except Exception as e:
        logger.error(f"Error fetching user lists: {e}")
        return []


    


@fcr.message(lambda msg: msg.text == "Create list", StateFilter.OPTION)
async def create_list_handler(message: types.Message, state: FSMContext):
    """
    Prompts the user to create a new list.
    """
    await message.reply("Enter the name of the new list:")
    await state.set_state(StateFilter.NEW_LIST)


@fcr.message(StateFilter.NEW_LIST)
async def process_new_list(message: types.Message, state: FSMContext):
    """
    Processes the creation of a new list.
    """
    list_name = message.text.strip()

    if not list_name:
        await message.reply("List name cannot be empty. Please enter a valid name.")
        return

    create_flashcard_list(message.from_user.id, list_name)
    await message.reply(f"List '{list_name}' created successfully.", reply_markup=MAINdata.reply_keyboard)

    # Return to the flashcard menu
    await state.set_state(StateFilter.OPTION)


@fcr.message(lambda msg: msg.text == "Choose list", StateFilter.OPTION)
async def choose_list_handler(message: types.Message, state: FSMContext):
    """
    Prompts the user to choose a list for adding or reviewing flashcards.
    """
    lists = get_user_lists(message.from_user.id)

    if not lists:
        await message.reply("You have no lists. Create a new list first.", reply_markup=MAINdata.reply_keyboard)
        return

    # Create a keyboard for list selection
    keyboard = [[KeyboardButton(text=list_name)] for _, list_name in lists]
    keyboard.append([KeyboardButton(text="Cancel")])  # Add "Cancel" button in a new row

    reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    await message.reply("Choose a list:", reply_markup=reply_markup)
    await state.set_state(StateFilter.CHOOSE_LIST)


@fcr.message(StateFilter.CHOOSE_LIST)
async def process_choose_list(message: types.Message, state: FSMContext):
    """
    Processes the user's choice of a list.
    """
    list_name = message.text.strip()

    if list_name == "Cancel":
        await message.reply("Cancelled.", reply_markup=MAINdata.reply_keyboard)
        await state.set_state(StateFilter.OPTION)
        return

    # Fetch the list ID
    lists = get_user_lists(message.from_user.id)
    selected_list = next((list_id for list_id, name in lists if name == list_name), None)

    if selected_list is None:
        await message.reply("Invalid list. Please choose a valid list.")
        return

    await state.update_data(selected_list=selected_list)
    await message.reply(f"List '{list_name}' selected.", reply_markup=MAINdata.reply_keyboard)

    # Return to the flashcard menu
    await state.set_state(StateFilter.OPTION)


@fcr.message(lambda msg: msg.text == "Delete list", StateFilter.OPTION)
async def delete_list_handler(message: types.Message, state: FSMContext):
    """
    Prompts the user to choose a list to delete.
    """
    lists = get_user_lists(message.from_user.id)

    if not lists:
        await message.reply("You have no lists to delete.", reply_markup=MAINdata.reply_keyboard)
        return

    # Create a keyboard for list selection
    keyboard = [[KeyboardButton(text=list_name)] for _, list_name in lists]
    keyboard.append([KeyboardButton(text="Cancel")])

    reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    await message.reply("Choose a list to delete:", reply_markup=reply_markup)
    await state.set_state(StateFilter.DELETE_LIST)



@fcr.message(StateFilter.DELETE_LIST)
async def process_delete_list(message: types.Message, state: FSMContext):
    """
    Processes the user's choice and deletes the selected list.
    """
    list_name = message.text.strip()

    if list_name == "Cancel":
        await message.reply("Deletion cancelled.", reply_markup=MAINdata.reply_keyboard)
        await state.set_state(StateFilter.OPTION)
        return

    # Fetch the list ID
    lists = get_user_lists(message.from_user.id)
    selected_list = next((list_id for list_id, name in lists if name == list_name), None)

    if selected_list is None:
        await message.reply("Invalid list. Please choose a valid list.")
        return

    try:
        # Delete the list and its associated flashcards
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("DELETE FROM flashcards WHERE list_id = %s AND user_id = %s"),
            (selected_list, message.from_user.id)
        )
        cur.execute(
            sql.SQL("DELETE FROM lists WHERE id = %s AND user_id = %s"),
            (selected_list, message.from_user.id)
        )
        conn.commit()
        cur.close()
        conn.close()

        await message.reply(f"List '{list_name}' and its flashcards have been deleted.", reply_markup=MAINdata.reply_keyboard)
    except Exception as e:
        await message.reply(f"An error occurred while deleting the list: {e}")
    finally:
        await state.set_state(StateFilter.OPTION)

    




@fcr.message(lambda msg: msg.text == "Add flashcard", StateFilter.OPTION)
async def add_flashcard_handler(message: types.Message, state: FSMContext):
    """
    Prompts the user to add a new flashcard to the selected list.
    """
    data = await state.get_data()
    selected_list = data.get("selected_list")

    if not selected_list:
        await message.reply("Please choose a list first.", reply_markup=MAINdata.reply_keyboard)
        return

    await message.reply("Write the new word in Chinese:")
    await state.set_state(StateFilter.NEW_WORD)


@fcr.message(StateFilter.NEW_WORD)
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
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL(
                """
                INSERT INTO flashcards (user_id, word, pinyin, context, list_id)
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






@fcr.message(lambda msg: msg.text == "See flashcards", StateFilter.OPTION)
async def see_flashcards_handler(message: types.Message, state: FSMContext):
    """
    Handles the 'See flashcards' button to display flashcards from the selected list.
    """
    try:
        # Get the selected list from the state
        user_data = await state.get_data()
        selected_list = user_data.get("selected_list")

        if not selected_list:
            await message.reply("You need to choose a list first.")
            return

        # Fetch flashcards from the database for the selected list
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT word, pinyin, context FROM flashcards WHERE user_id = %s AND list_id = %s"),
            (message.from_user.id, selected_list)
        )
        flashcards = cur.fetchall()
        cur.close()
        conn.close()

        if flashcards:
            # Display flashcards with Chinese characters, Pinyin, and translation
            response = f"Flashcards from the selected list:\n"
            for idx, (word, pinyin, translation) in enumerate(flashcards, start=1):
                response += f"{idx}. {word} ({pinyin}): {translation}\n"
            await message.reply(response)
        else:
            await message.reply("This list has no flashcards.")
    except Exception as e:
        await message.reply(f"An error occurred while fetching flashcards: {e}")


@fcr.message(lambda msg: msg.text == "Delete flashcard", StateFilter.OPTION)
async def delete_flashcard_handler(message: types.Message, state: FSMContext):
    """
    Handles the 'Delete flashcard' button to prompt the user for a word to delete.
    """
    await message.reply("Write the word of the flashcard you want to delete:")
    await state.set_state(StateFilter.DELETE_WORD)


@fcr.message(StateFilter.DELETE_WORD)
async def process_delete_flashcard(message: types.Message, state: FSMContext):
    """
    Processes the deletion of a flashcard by word.
    """
    word_to_delete = message.text.strip()

    try:
        # Delete flashcard from the database
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL(
                "DELETE FROM flashcards WHERE user_id = %s AND word = %s RETURNING word"
            ),
            (message.from_user.id, word_to_delete)
        )
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if deleted:
            await message.reply(f"Flashcard '{word_to_delete}' has been deleted.", reply_markup=MAINdata.reply_keyboard)
        else:
            await message.reply(f"No flashcard found with the word '{word_to_delete}'.", reply_markup=MAINdata.reply_keyboard)
    except Exception as e:
        await message.reply(f"An error occurred while deleting the flashcard: {e}", reply_markup=MAINdata.reply_keyboard)

    # Reset state back to main flashcard menu
    await state.set_state(StateFilter.OPTION)


@fcr.message(lambda msg: msg.text == "Review flashcards", StateFilter.OPTION)
async def review_flashcards_handler(message: types.Message, state: FSMContext):
    """
    Handles the 'Review flashcards' button by starting a review of flashcards from the selected list.
    """
    data = await state.get_data()
    selected_list = data.get("selected_list")

    if not selected_list:
        await message.reply("Please choose a list first.")
        return

    try:
        # Fetch flashcards from the selected list
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT word, context FROM flashcards WHERE user_id = %s AND list_id = %s"),
            (message.from_user.id, selected_list)
        )
        flashcards = cur.fetchall()
        cur.close()
        conn.close()

        if flashcards:
            # Store flashcards in the state and start reviewing
            await state.update_data(flashcards=flashcards, current_index=0)
            await show_next_flashcard(message, state)
        else:
            await message.reply("This list has no flashcards to review.")
    except Exception as e:
        await message.reply(f"An error occurred while fetching flashcards: {e}")

async def show_next_flashcard(message: types.Message, state: FSMContext):
    """
    Shows the next flashcard to the user.
    """
    data = await state.get_data()
    flashcards = data.get("flashcards", [])
    current_index = data.get("current_index", 0)

    if current_index < len(flashcards):
        word, _ = flashcards[current_index]
        await message.answer(f"Word: {word}\nTry to remember its context. When you're ready, type 'show'.")
    else:
        await message.reply("You have reviewed all flashcards!")
        await state.update_data(flashcards=None, current_index=None)  # Clear review data


@fcr.message(lambda msg: msg.text.lower() == "show", StateFilter.OPTION)
async def show_flashcard_context(message: types.Message, state: FSMContext):
    """
    Shows the context of the currently reviewed flashcard and proceeds to the next one.
    """
    data = await state.get_data()
    flashcards = data.get("flashcards", [])
    current_index = data.get("current_index", 0)

    if current_index < len(flashcards):
        word, context = flashcards[current_index]
        await message.reply(f"Word: {word}\nContext: {context}")
        
        # Move to the next flashcard
        current_index += 1
        await state.update_data(current_index=current_index)
        await show_next_flashcard(message, state)
    else:
        await message.reply("No more flashcards to review.")
        await state.update_data(flashcards=None, current_index=None)  # Clear review data

















@fcr.message(lambda msg: msg.text == "Learn flashcards", StateFilter.OPTION)
async def learn_flashcards_handler(message: types.Message, state: FSMContext):
    """
    Handles the 'Learn flashcards' button by starting a learning session from the selected list.
    """
    data = await state.get_data()
    selected_list = data.get("selected_list")
    if not selected_list:
        await message.reply("Please choose a list first.")
        return

    try:
        # Fetch flashcards from the selected list
        conn = psycopg2.connect(MAINdata.DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT word, context FROM flashcards WHERE user_id = %s AND list_id = %s"),
            (message.from_user.id, selected_list)
        )
        flashcards = cur.fetchall()
        cur.close()
        conn.close()

        if flashcards:
            random.shuffle(flashcards)  # Shuffle flashcards for random order

            await state.update_data(
                flashcards=flashcards,
                current_index=0,
                task_progress={word: {
                    "translate_to_chinese": False, 
                    "translate_to_english": False, 
                    "context_completion": False,
                    "multiple_choice": False
                    }
                    for word, _ in flashcards},
                
            )

            await show_next_learning_task(message, state)
        else:
            await message.reply("This list has no flashcards to learn.")
    except Exception as e:
        await message.reply(f"An error occurred while fetching flashcards: {e}")



async def show_next_learning_task(message: types.Message, state: FSMContext):
    """
    Выбирает и отправляет следующее задание пользователю.
    """
    data = await state.get_data()
    flashcards = data.get("flashcards", [])
    task_progress = data.get("task_progress", {})

    if not flashcards:
        await message.answer("⚠️ No flashcards found.")
        return

    if all(all(task_done for task_done in progress.values()) for progress in task_progress.values()):
        await message.answer("🎉 You have completed learning this set!", reply_markup=MAINdata.main_menu)
        await state.clear()
        return

    word = random.choice([w for w, tasks in task_progress.items() if not all(tasks.values())])
    context = next(ctx for w, ctx in flashcards if w == word)

    available_tasks = [task for task, done in task_progress[word].items() if not done]
    if not available_tasks:
        await show_next_learning_task(message, state)
        return

    task_type = random.choice(available_tasks)

    if task_type == "translate_to_chinese":
        await message.answer(f"📝 Translate this word into Chinese: {context}")
        await state.update_data(current_task="translate_to_chinese", correct_answer=word, current_word=word, current_task_type=task_type)
        await state.set_state(StateFilter.INPUT_HANZI)

    elif task_type == "translate_to_english":
        await message.answer(f"📝 Translate this word into English: {word}")
        await state.update_data(current_task="translate_to_english", correct_answer=context, current_word=word, current_task_type=task_type)
        await state.set_state(StateFilter.INPUT_TRANSLATION)

    elif task_type == "context_completion":
        await message.answer(f"📝 Complete the context for this word: {word}\nExample: {context[:len(context)//2]}...")
        await state.update_data(current_task="context_completion", correct_answer=context, current_word=word, current_task_type=task_type)
        await state.set_state(StateFilter.INPUT_TRANSLATION)

    elif task_type == "multiple_choice":
        gener = random.randint(2, 5)
        # Создаем inline-клавиатуру с вариантами ответа
        incorrect_options = [ctx for w, ctx in flashcards if w != word][:gener - 1]
        options = [context] + incorrect_options
        random.shuffle(options)

        # ✅ Исправленный код: передаем список кнопок в `InlineKeyboardMarkup`
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=option, callback_data=f"answer_{option}")] for option in options
            ]
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
            [InlineKeyboardButton(text=option, callback_data=f"answer_{option}")] for option in options
            ]
            )

        await message.answer(f"❓ Choose the correct meaning of '{word}':", reply_markup=keyboard)

        await state.update_data(
            current_task="multiple_choice",
            correct_answer=context,
            current_word=word,
            current_task_type=task_type
        )


@fcr.callback_query(lambda c: c.data.startswith("answer_"))
async def handle_button_choice(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор ответа через inline-кнопки.
    """
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    current_word = data.get("current_word")
    task_progress = data.get("task_progress")

    selected_answer = callback_query.data.replace("answer_", "")

    if selected_answer == correct_answer:
        task_progress[current_word]["multiple_choice"] = True
        await state.update_data(task_progress=task_progress)

        await callback_query.message.answer("✅ Correct!")
        await callback_query.answer()

        # Переход к следующему заданию
        await show_next_learning_task(callback_query.message, state)
    else:
        await callback_query.message.answer("❌ Incorrect. Try again!")
        await callback_query.answer()


@fcr.message(StateFilter.INPUT_HANZI)
async def check_hanzi_input(message: types.Message, state: FSMContext):
    """
    Checks if the user's input matches the expected Chinese translation.
    """
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    current_word = data.get("current_word")
    current_task_type = data.get("current_task_type")
    task_progress = data.get("task_progress")

    if message.text == correct_answer:
        await message.reply("Correct!")
        task_progress[current_word][current_task_type] = True
    else:
        await message.reply(f"Incorrect. The correct answer is: {correct_answer}")

    await state.update_data(task_progress=task_progress)
    await show_next_learning_task(message, state)


@fcr.message(StateFilter.INPUT_TRANSLATION)
async def check_translation_input(message: types.Message, state: FSMContext):
    """
    Checks if the user's input matches the expected English translation or completes the context.
    """
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    current_word = data.get("current_word")
    current_task_type = data.get("current_task_type")
    task_progress = data.get("task_progress")

    if message.text.lower() == correct_answer.lower():
        await message.reply("Correct!")
        task_progress[current_word][current_task_type] = True
    else:
        await message.reply(f"Incorrect. The correct answer is: {correct_answer}")

    await state.update_data(task_progress=task_progress)
    await show_next_learning_task(message, state)
































@fcr.message(lambda msg: msg.text == "Done", StateFilter.OPTION)
async def done_handler(message: types.Message, state: FSMContext):
    """
    Handles the 'Done' button to exit the flashcard menu.
    """
    await state.clear()
    await message.answer(
        "Exiting the flashcard menu. Back to the main menu!",
        reply_markup=MAINdata.main_menu)








