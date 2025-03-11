import os
import json
import hmac
import hashlib
import time
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from aiogram.utils import executor

# Вставьте сюда токен, который вы получили от @BotFather
# Пример: BOT_TOKEN = "5555555555:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAaa"
BOT_TOKEN = "7747362614:AAFCKvVQ0pes_iwoCrPKOBKc3YTPpjkZkxs"
# URL вашего приложения на GitHub Pages
WEBAPP_URL = "https://askulibaba.github.io/enigma-telegram-app/login.html"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Хранилище сессий (в реальном приложении лучше использовать базу данных)
sessions = {}

def verify_telegram_data(data):
    """Проверка подлинности данных от Telegram Login Widget"""
    if 'hash' not in data:
        return False
    
    auth_data = data.copy()
    auth_hash = auth_data.pop('hash')
    
    data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(auth_data.items())])
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    
    hash_str = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hash_str == auth_hash

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
        data = json.loads(message.web_app_data.data)
        
        if data.get('type') == 'auth':
            auth_data = data.get('data', {})
            if verify_telegram_data(auth_data):
                user_id = str(auth_data.get('id'))
                sessions[user_id] = {
                    'auth_date': auth_data.get('auth_date'),
                    'first_name': auth_data.get('first_name'),
                    'last_name': auth_data.get('last_name'),
                    'username': auth_data.get('username')
                }
                await message.answer("Авторизация успешна!")
            else:
                await message.answer("Ошибка авторизации: недействительные данные")
        else:
            # Обработка зашифрованного текста
            user_id = str(message.from_user.id)
            if user_id in sessions:
                await message.answer(f"Зашифрованный текст: {data}")
            else:
                await message.answer("Пожалуйста, авторизуйтесь заново")
                
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True) 