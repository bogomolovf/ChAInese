from zi_identification import zi_identification_router, ZiIdentificationStates
from lessons.lesson_0 import lesson_zero_router, LessonZeroStates
from aiogram.fsm.storage.memory import MemoryStorage
from flashcards import fcr, StateFilter, init_db
from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import MAINdata
import asyncio
import logging

import psycopg2
from aiogram.fsm.state import StatesGroup, State
from profile_registration import RegistrationStates, save_user, get_user_profile, is_user_registered
from profile_registration import prr
from flashcards import get_user_lists
from psycopg2 import sql


dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)




















    
@dp.message(Command("start"))
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


@dp.message(RegistrationStates.waiting_for_nickname)
async def nickname_handler(message: Message, state: FSMContext):
    nickname = message.text.strip()
    if not nickname:
        await message.reply("Никнейм не может быть пустым. Пожалуйста, введите ваш никнейм:")
        return

    await state.update_data(nickname=nickname)
    await state.set_state(RegistrationStates.waiting_for_email)
    await message.reply("Отлично! Теперь введите ваш адрес электронной почты:")


# Email handler
@dp.message(RegistrationStates.waiting_for_email)
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
















@dp.message(lambda message: message.text in ["Изучение китайского с нуля", "Подготовка к HSK", "Распознать иероглиф", "Карточки", "Мой профиль"])
async def menu_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state is not None:
        if current_state in [LessonZeroStates.waiting_for_name.state, ZiIdentificationStates.waiting_for_image.state]:
            await message.reply("Вы не можете выполнить эту команду, пока не завершите текущую.")
            return

    if message.text == "Изучение китайского с нуля":
        await state.set_state(LessonZeroStates.waiting_for_name)
        user_id = message.from_user.id

    # Check if the user is registered
        if is_user_registered(user_id):
            await state.set_state(LessonZeroStates.waiting_for_name)  # Set the lesson state
            await message.answer("Вы выбрали изучение китайского с нуля. Начнем урок!")
        # Optionally, trigger the next step of the lesson here
        else:
            await message.answer("Вы еще не зарегистрированы. Пожалуйста, зарегистрируйтесь через команду /start.")

    elif message.text == "Подготовка к HSK":
        await message.answer("Вы выбрали подготовку к HSK. В разработке!")

    elif message.text == "Распознать иероглиф":
        if current_state != ZiIdentificationStates.waiting_for_image.state:
            await message.reply("Отправьте фото с иероглифами для распознавания.")
            await state.set_state(ZiIdentificationStates.waiting_for_image)

    elif message.text == "Карточки":
        await message.reply(
        "Выберите что планируете сделать:",
        reply_markup=MAINdata.first_markup,
    )
        await state.set_state(StateFilter.OPTION)

    elif message.text == "Мой профиль":

        user_id = message.from_user.id
        user, email, flashcards = get_user_profile(user_id)
        lists = get_user_lists(message.from_user.id)


        if not lists:
            await message.reply("You have no lists created.")
            return

        if user:
            nickname = user[0]
            profile_message = f"Ваш профиль:\nНикнейм: {nickname}\nПочта: {email}\n"

            await message.answer(profile_message)
        else:
            await message.answer("Ваш профиль не найден. Пожалуйста, зарегистрируйтесь снова через команду /start.")



        response = "Ваши списки:\n\n"

        for list_id, list_name in lists:
            response += f"List: {list_name}\n"

        # Fetch flashcards for this list
            conn = psycopg2.connect(MAINdata.DATABASE_URL)
            cur = conn.cursor()
            cur.execute(
                sql.SQL("SELECT word, pinyin, context FROM flashcards WHERE list_id = %s"),
                (list_id,)
            )
            flashcards = cur.fetchall()
            cur.close()
            conn.close()

            if flashcards:
                for word, pinyin, context in flashcards:
                    response += f"- {word}({pinyin}): {context}\n"
            else:
                response += "- No flashcards\n"
            response += "\n"

        await message.answer(response)


async def main():
    print("Бот запущен!")
    
    init_db()

    dp.include_router(lesson_zero_router)
    dp.include_router(zi_identification_router)
    dp.include_router(fcr)
    dp.include_router(prr)


    await dp.start_polling(MAINdata.bot)

if __name__ == "__main__":
    asyncio.run(main())


