from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db_execute
import random
import logging
import utils.keyboards

router = Router()
logger = logging.getLogger(__name__)

### ✅ Начало изучения карточек
@router.message(F.text == "Карточки")
async def learn_flashcards_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    selected_list = data.get("selected_list")

    if not selected_list:
        await message.reply("⚠️ Пожалуйста, выберите список карточек перед началом обучения.", 
                            reply_markup=utils.keyboards.first_markup)
        return

    try:
        flashcards = await db_execute(
            "SELECT word, context FROM flashcards WHERE user_id = %s AND list_id = %s",
            (message.from_user.id, selected_list),
        )

        if flashcards:
            random.shuffle(flashcards)
            await state.update_data(
                flashcards=flashcards,
                current_index=0,
                task_progress={word: {
                    "translate_to_chinese": False, 
                    "translate_to_english": False, 
                    "context_completion": False,
                    "multiple_choice": False
                } for word, _ in flashcards}
            )
            await show_next_learning_task(message, state)
        else:
            await message.reply("⚠️ Этот список карточек пуст.")
    except Exception as e:
        await message.reply(f"❌ Ошибка при загрузке карточек: {e}")

### ✅ Показ следующего задания
async def show_next_learning_task(message: types.Message, state: FSMContext):
    data = await state.get_data()
    flashcards = data.get("flashcards", [])
    task_progress = data.get("task_progress", {})

    if not flashcards:
        await message.answer("⚠️ Ошибка: Карточки не найдены.")
        return

    if all(all(task_done for task_done in progress.values()) for progress in task_progress.values()):
        await message.answer("🎉 Вы завершили изучение набора карточек!", reply_markup=types.ReplyKeyboardRemove())
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
        await message.answer(f"📝 Переведите это слово на китайский: {context}")
        await state.update_data(current_task="translate_to_chinese", correct_answer=word, current_word=word, current_task_type=task_type)
        await state.set_state(StateFilter("INPUT_HANZI"))

    elif task_type == "translate_to_english":
        await message.answer(f"📝 Переведите это слово на английский: {word}")
        await state.update_data(current_task="translate_to_english", correct_answer=context, current_word=word, current_task_type=task_type)
        await state.set_state(StateFilter("INPUT_TRANSLATION"))

    elif task_type == "context_completion":
        await message.answer(f"📝 Завершите контекст для слова: {word}\nПример: {context[:len(context)//2]}...")
        await state.update_data(current_task="context_completion", correct_answer=context, current_word=word, current_task_type=task_type)
        await state.set_state(StateFilter("INPUT_TRANSLATION"))

    elif task_type == "multiple_choice":
        incorrect_options = [ctx for w, ctx in flashcards if w != word][:3]
        options = [context] + incorrect_options
        random.shuffle(options)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=option, callback_data=f"answer_{option}")] for option in options
            ]
        )

        await message.answer(f"❓ Выберите правильный перевод '{word}':", reply_markup=keyboard)
        await state.update_data(current_task="multiple_choice", correct_answer=context, current_word=word, current_task_type=task_type)

### ✅ Проверка множественного выбора
@router.callback_query(lambda c: c.data.startswith("answer_"))
async def handle_button_choice(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    current_word = data.get("current_word")
    task_progress = data.get("task_progress")

    selected_answer = callback_query.data.replace("answer_", "")

    if selected_answer == correct_answer:
        task_progress[current_word]["multiple_choice"] = True
        await state.update_data(task_progress=task_progress)
        await callback_query.message.answer("✅ Верно!")
        await callback_query.answer()
        await show_next_learning_task(callback_query.message, state)
    else:
        await callback_query.message.answer("❌ Неверно. Попробуйте еще раз!")
        await callback_query.answer()

### ✅ Проверка ввода китайских иероглифов
@router.message(StateFilter("INPUT_HANZI"))
async def check_hanzi_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    current_word = data.get("current_word")
    current_task_type = data.get("current_task_type")
    task_progress = data.get("task_progress")

    if message.text == correct_answer:
        await message.reply("✅ Правильно!")
        task_progress[current_word][current_task_type] = True
    else:
        await message.reply(f"❌ Неправильно. Верный ответ: {correct_answer}")

    await state.update_data(task_progress=task_progress)
    await show_next_learning_task(message, state)

### ✅ Проверка перевода и контекста
@router.message(StateFilter("INPUT_TRANSLATION"))
async def check_translation_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    current_word = data.get("current_word")
    current_task_type = data.get("current_task_type")
    task_progress = data.get("task_progress")

    if message.text.lower() == correct_answer.lower():
        await message.reply("✅ Правильно!")
        task_progress[current_word][current_task_type] = True
    else:
        await message.reply(f"❌ Неправильно. Верный ответ: {correct_answer}")

    await state.update_data(task_progress=task_progress)
    await show_next_learning_task(message, state)
