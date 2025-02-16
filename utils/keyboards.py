from aiogram.types import ReplyKeyboardMarkup, KeyboardButton



main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изучение китайского с нуля")],
        [KeyboardButton(text="Подготовка к HSK")],
        [KeyboardButton(text="Распознать иероглиф")],
        [KeyboardButton(text="Карточки")],
        [KeyboardButton(text="Мой профиль")],
    ],
    resize_keyboard=True
)

reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add flashcard"), KeyboardButton(text="See flashcards")],
        [KeyboardButton(text="Delete flashcard"), KeyboardButton(text="Review flashcards")], 
        [KeyboardButton(text="Learn flashcards"), KeyboardButton(text="Done")],
    ],
    resize_keyboard=True
)

first_markup = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Create list")],
        [KeyboardButton(text="Choose list")],
        [KeyboardButton(text="Delete list")],
    ],
    resize_keyboard=True
)
