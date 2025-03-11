import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from aiogram.utils import executor

# Замените на свой токен бота
BOT_TOKEN = "YOUR_BOT_TOKEN"
# Замените на URL, где будет размещено ваше веб-приложение
WEBAPP_URL = "YOUR_WEBAPP_URL"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(
        text="Открыть шифрование Энигма",
        web_app=WebAppInfo(url=WEBAPP_URL)
    ))
    
    await message.answer(
        "Привет! Это бот для шифрования текста методом Энигма.\n"
        "Нажмите на кнопку ниже, чтобы открыть приложение.",
        reply_markup=markup
    )

@dp.message_handler(content_types=['web_app_data'])
async def web_app_handler(message: types.Message):
    try:
        data = message.web_app_data.data
        # Здесь можно добавить обработку данных от веб-приложения
        await message.answer(f"Зашифрованный текст: {data}")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True) 