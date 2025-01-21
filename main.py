from lessons.lesson_0 import lesson_zero_router, LessonZeroStates
from zi_identification import zi_identification_router, ZiIdentificationStates
from flashcards import flashcard_router
import MAINdata


from aiogram import Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
import asyncio
import logging
import pytesseract


pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'



# Создаем бота и диспетчер

dp = Dispatcher(storage=MemoryStorage())



# Клавиатура главного меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изучение китайского с нуля")],
        [KeyboardButton(text="Подготовка к HSK")],
        [KeyboardButton(text="Распознать иероглиф")],
    ],
    resize_keyboard=True
)

# Приветственное сообщение
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "Добро пожаловать в бота для изучения китайского языка! Выберите, с чего начать:",
        reply_markup=main_menu
    )


# Обработка кнопок главного меню
@dp.message(lambda message: message.text in ["Изучение китайского с нуля", "Подготовка к HSK", "Распознать иероглиф"])
async def menu_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

    current_state = await state.get_state()

    if current_state is not None:
        if current_state in [LessonZeroStates.waiting_for_name.state, ZiIdentificationStates.waiting_for_image.state]:
            await message.reply("Вы не можете выполнить эту команду, пока не завершите текущую.")
            return

    if message.text == "Изучение китайского с нуля":
        await state.set_state(LessonZeroStates.waiting_for_name)
        await message.answer("Вы выбрали изучение китайского с нуля. Давайте начнем с небольшой регистрации.")
        await asyncio.sleep(1)
        await message.answer("Введите ваше имя:")

    elif message.text == "Подготовка к HSK":
        await message.answer("Вы выбрали подготовку к HSK. В разработке!")

    elif message.text == "Распознать иероглиф":
        if current_state != ZiIdentificationStates.waiting_for_image.state:
            await message.reply("Отправьте фото с иероглифами для распознавания.")
            await state.set_state(ZiIdentificationStates.waiting_for_image)

    elif message.text == "Карточки":
        await flashcard_router.start_handler(message, state)





# Главная функция для запуска бота
async def main():
    print("Бот запущен!")
    # Регистрация роутеров
    dp.include_router(lesson_zero_router)
    dp.include_router(zi_identification_router)
    dp.include_router(flashcard_router)
    
    await dp.start_polling(MAINdata.bot)

# Точка входа
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
