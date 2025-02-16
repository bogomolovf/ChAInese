from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database.db import db_execute
import logging
from aiogram.filters import StateFilter
from aiogram.filters import Command
import utils.keyboards

router = Router()
logger = logging.getLogger(__name__)

### ✅ Получение списков пользователя
async def get_user_lists(user_id):
    """Возвращает список наборов карточек пользователя"""
    try:
        rows = await db_execute("SELECT id, list_name FROM lists WHERE user_id = ?", (user_id,))
        return rows
    except Exception as e:
        logger.error(f"❌ Error fetching user lists: {e}")
        return []

### ✅ Создание списка
@router.message(F.text == "Create list")
async def create_list_handler(message: types.Message, state: FSMContext):
    """Запрос имени нового списка"""
    await message.answer("✏️ Введите название нового списка:")
    await state.set_state("new_list")

@router.message(StateFilter("new_list"))
async def process_new_list(message: types.Message, state: FSMContext):
    """Создает новый список карточек"""
    list_name = message.text.strip()

    if not list_name:
        await message.answer("⚠️ Название списка не может быть пустым. Попробуйте еще раз.")
        return

    try:
        await db_execute("INSERT INTO lists (user_id, list_name) VALUES (?, ?)", (message.from_user.id, list_name))
        await message.answer(f"✅ Список **'{list_name}'** успешно создан!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании списка: {e}")

    await state.clear()

### ✅ Просмотр всех списков
@router.message(StateFilter("My lists"))
async def view_lists_handler(message: types.Message):
    """Показывает пользователю его списки карточек"""
    lists = await get_user_lists(message.from_user.id)

    if not lists:
        await message.answer("⚠️ У вас пока нет списков. Создайте новый список с помощью кнопки **'Create list'**.")
        return

    response = "📂 **Ваши списки карточек:**\n"
    for idx, (list_id, list_name) in enumerate(lists, start=1):
        response += f"{idx}. {list_name} (ID: {list_id})\n"

    await message.answer(response)

### ✅ Выбор списка для работы
@router.message(lambda msg: msg.text == "Choose list", StateFilter.OPTION)
async def choose_list_handler(message: types.Message, state: FSMContext):
    """
    Prompts the user to choose a list for adding or reviewing flashcards.
    """
    lists = get_user_lists(message.from_user.id)

    if not lists:
        await message.reply("You have no lists. Create a new list first.", reply_markup=utils.keyboards.first_markup)
        return

    # Create a keyboard for list selection
    keyboard = [[KeyboardButton(text=list_name)] for _, list_name in lists]
    keyboard.append([KeyboardButton(text="Cancel")])  # Add "Cancel" button in a new row

    reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    await message.reply("Choose a list:", reply_markup=reply_markup)
    await state.set_state("choose_list")

@router.message(StateFilter("choose_list"))
async def process_choose_list(message: types.Message, state: FSMContext):
    """Обрабатывает выбор списка пользователем"""
    list_name = message.text.strip()

    if list_name == "Cancel":
        await message.answer("🚫 Отменено.", reply_markup=ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True))
        await state.clear()
        return

    lists = await get_user_lists(message.from_user.id)
    selected_list = next((list_id for list_id, name in lists if name == list_name), None)

    if selected_list is None:
        await message.answer("⚠️ Неверное название списка. Выберите из предложенных вариантов.")
        return

    await state.update_data(selected_list=selected_list)
    await message.answer(f"✅ Список **'{list_name}'** выбран!", reply_markup=ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True))
    await state.clear()

### ✅ Удаление списка
@router.message(F.text == "Delete list")
async def delete_list_handler(message: types.Message, state: FSMContext):
    """Запрашивает список для удаления"""
    lists = await get_user_lists(message.from_user.id)

    if not lists:
        await message.answer("⚠️ У вас нет списков для удаления.")
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=list_name)] for _, list_name in lists] + [[KeyboardButton(text="Cancel")]],
        resize_keyboard=True
    )

    await message.answer("📂 Выберите список для удаления:", reply_markup=keyboard)
    await state.set_state("delete_list")

@router.message(StateFilter("delete_list"))
async def process_delete_list(message: types.Message, state: FSMContext):
    """Удаляет выбранный список карточек"""
    list_name = message.text.strip()

    if list_name == "Cancel":
        await message.answer("🚫 Удаление отменено.", reply_markup=ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True))
        await state.clear()
        return

    lists = await get_user_lists(message.from_user.id)
    selected_list = next((list_id for list_id, name in lists if name == list_name), None)

    if selected_list is None:
        await message.answer("⚠️ Неверное название списка. Попробуйте снова.")
        return

    try:
        await db_execute("DELETE FROM flashcards WHERE list_id = ?", (selected_list,))
        await db_execute("DELETE FROM lists WHERE id = ?", (selected_list,))
        await message.answer(f"🗑️ Список **'{list_name}'** и его карточки удалены.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении списка: {e}")

    await state.clear()

    