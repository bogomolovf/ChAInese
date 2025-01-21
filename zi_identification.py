from deep_translator import GoogleTranslator
import pytesseract
from PIL import Image
from pypinyin import pinyin, Style
from io import BytesIO
from aiogram import Router, types
from MAINdata import bot, BOT_TOKEN
from aiogram.fsm.state import StatesGroup, State

zi_identification_router = Router()

class ZiIdentificationStates(StatesGroup):
    waiting_for_image = State()

@zi_identification_router.message(lambda message: message.photo is not None)
async def handle_image(message: types.Message):
    photo = message.photo[-1]  # Получаем максимальное фото

    file_info = await bot.get_file(photo.file_id)

    # Открываем изображение с помощью PIL
    
    file_path = file_info.file_path
    file = await bot.download_file(file_path)

    img = Image.open(file)


    # Применяем OCR для распознавания текста
    text = pytesseract.image_to_string(img, lang='chi_sim')  # Для китайского языка используем lang='chi_sim'

    # Отправляем результат распознавания
    if text:

        pinyin_text = ' '.join([''.join(p) for p in pinyin(text, style=Style.TONE)])
        
        translated_text = GoogleTranslator(source='zh-CN', target='ru').translate(text)

        response_message = f"Распознанный текст: {text}\n\nПиньинь: {pinyin_text}\nПеревод: {translated_text}"

        await message.reply(response_message)


    else:
        await message.reply("Не удалось распознать текст.")