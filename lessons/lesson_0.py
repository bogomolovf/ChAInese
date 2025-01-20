from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import asyncio

# Инициализируем роутер
lesson_zero_router = Router()

# Определяем состояния для урока
class LessonZeroStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_hello = State()
    waiting_for_thank_you = State()

# Обработчик регистрации
@lesson_zero_router.message(LessonZeroStates.waiting_for_name)
async def register_name_handler(message: Message, state: FSMContext):

    user_id = message.from_user.id

    # Получаем данные из контекста FSM
    data = await state.get_data()
    
    # Записываем имя пользователя в данные состояния
    user_data = data.get('users_db', {})
    user_data[user_id] = {"name": message.text}
    
    # Обновляем данные в контексте
    await state.update_data(users_db=user_data)

    # Приветствие и начало урока
    await message.answer(f"Приятно познакомиться, {message.text}! Теперь начнем ваш первый урок.")
    await start_lesson_zero(message, state)  # Начинаем первый урок




# Урок 1: Изучение китайского с нуля
async def start_lesson_zero(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await message.answer("Урок 1: Приветствие\nИероглиф: 你好 (nǐ hǎo) — Привет\n\nПовторите и введите транскрипцию пиньинь:")
    await state.set_state(LessonZeroStates.waiting_for_hello)

@lesson_zero_router.message(LessonZeroStates.waiting_for_hello)
async def lesson_zero_hello_handler(message: Message, state: FSMContext):
    if message.text.lower() == "nǐ hǎo":
        await message.answer("Отлично! Теперь разберем ещё одно слово.\nИероглиф: 谢谢 (xiè xie) — Спасибо\n\nВведите транскрипцию пиньинь:")
        await state.set_state(LessonZeroStates.waiting_for_thank_you)
    else:
        await message.answer("Неправильно. Попробуйте ещё раз. Подсказка: nǐ hǎo")

@lesson_zero_router.message(LessonZeroStates.waiting_for_thank_you)
async def lesson_zero_thank_you_handler(message: Message, state: FSMContext):
    if message.text.lower() == "xiè xie":
        await message.answer("Отлично, вы справились с первым уроком! Возвращайтесь завтра для нового урока.")
        await state.clear()
    else:
        await message.answer("Неправильно. Попробуйте ещё раз. Подсказка: xiè xie")



