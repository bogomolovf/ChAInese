from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
from io import BytesIO
from pypinyin import pinyin, Style
from aiogram import Router, types
from MAINdata import bot, BOT_TOKEN
from aiogram.fsm.state import StatesGroup, State
import numpy as np
import logging
from deep_translator import GoogleTranslator

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

zi_identification_router = Router()

class ZiIdentificationStates(StatesGroup):
    waiting_for_image = State()

# Инициализируем PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='ch')

@zi_identification_router.message(lambda message: message.photo is not None)
async def handle_image(message: types.Message):
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        file = await bot.download_file(file_info.file_path)
    
        img = Image.open(file).convert('RGB')
        img_np = np.array(img)
    
        result = ocr.ocr(img_np, cls=True)
        logger.info(f"OCR Result: {result}")
    
        if result and len(result[0]) > 0:
            extracted_text = '\n'.join([line[1][0] for line in result[0]])
            logger.info(f"Extracted text: {extracted_text}")
        
            pinyin_text = ' '.join([''.join(p) for p in pinyin(extracted_text, style=Style.TONE)])
            translated_text = GoogleTranslator(source='zh-CN', target='ru').translate(extracted_text)
        
            response_message = f"Распознанный текст: {extracted_text}\n\nПиньинь: {pinyin_text}\nПеревод: {translated_text}"
            await message.reply(response_message)
        else:
            await message.reply("Не удалось распознать текст.")
    except Exception as e:
        logger.error(f"Ошибка обработки изображения: {e}")
        await message.reply("Произошла ошибка при обработке изображения. Попробуйте снова.")