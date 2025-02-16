from aiogram.fsm.state import StatesGroup, State
from deep_translator import GoogleTranslator
from pypinyin import pinyin, Style
from aiogram import Router, types
from MAINdata import bot
from PIL import Image
import pytesseract


zi_identification_router = Router()

class ZiIdentificationStates(StatesGroup):
    waiting_for_image = State()

@zi_identification_router.message(lambda message: message.photo is not None)
async def handle_image(message: types.Message):
    photo = message.photo[-1]

    file_info = await bot.get_file(photo.file_id) 
    file_path = file_info.file_path
    file = await bot.download_file(file_path)

    img = Image.open(file)

    text = pytesseract.image_to_string(img, lang='chi_sim')

    if text:

        pinyin_text = ' '.join([''.join(p) for p in pinyin(text, style=Style.TONE)])
        
        translated_text = GoogleTranslator(source='zh-CN', target='ru').translate(text)

        response_message = f"Распознанный текст: {text}\n\nПиньинь: {pinyin_text}\nПеревод: {translated_text}"

        await message.reply(response_message)


    else:
        await message.reply("Не удалось распознать текст.")