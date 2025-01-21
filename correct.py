from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
from io import BytesIO
from pypinyin import pinyin, Style
from aiogram import Router, types
from MAINdata import bot, BOT_TOKEN
from aiogram.fsm.state import StatesGroup, State
import numpy as np
from deep_translator import GoogleTranslator
import cv2


zi_identification_router = Router()

class ZiIdentificationStates(StatesGroup):
    waiting_for_image = State()

# Инициализируем PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='ch', ocr_version='PP-OCRv3')

@zi_identification_router.message(lambda message: message.photo is not None)
async def handle_image(message: types.Message):
    try:
        photo = message.photo[-1]  # Получаем максимальное фото

        # Получаем информацию о файле через Telegram API
        file_info = await bot.get_file(photo.file_id)
        
        file_path = file_info.file_path
        file = await bot.download_file(file_path)

        # Конвертируем байты в изображение
        img = Image.open(file).convert("L")

        threshold_value = 200
        # Anything above 200 => white; anything below => black
        binary_image = img.point(lambda p: 255 if p > threshold_value else 0, '1')

        img_np = np.array(img)
        
        img_cv2 = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        # Применяем пороговое преобразование для бинаризации изображения
        gray = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2GRAY)
        _, binary_image = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        # Используем PaddleOCR для распознавания текста
        result = ocr.ocr(binary_image, cls=True)
        


        if result and len(result[0]) > 0:
            # Извлекаем распознанный текст
            extracted_text = '\n'.join([line[1][0] for line in result[0]])

            # Конвертируем текст в пиньинь
            pinyin_text = ' '.join([''.join(p) for p in pinyin(extracted_text, style=Style.TONE)])

            # Перевод текста с китайского на русский
            translated_text = GoogleTranslator(source='zh-CN', target='ru').translate(extracted_text)

            # Формируем ответное сообщение
            response_message = (
                f"Распознанный текст: {extracted_text}\n\n"
                f"Пиньинь: {pinyin_text}\n"
                f"Перевод: {translated_text}"
            )
            await message.reply(response_message)
        else:
            await message.reply("Не удалось распознать текст.")

    except Exception as e:
        await message.reply(f"Произошла ошибка при обработке изображения: {str(e)}")
        
#
#Думаем...
#