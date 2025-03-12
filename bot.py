import os
import json
import hmac
import hashlib
import time
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from telethon import TelegramClient
from telethon.tl.types import Dialog, User, Chat, Channel
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from dotenv import load_dotenv
from flask import Flask, send_from_directory, jsonify, request
import asyncio
from threading import Thread

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PORT = int(os.getenv('PORT', 5000))
HOST = os.getenv('HOST', '0.0.0.0')
APP_URL = os.getenv('APP_URL', f'https://{os.getenv("RAILWAY_STATIC_URL", "localhost:5000")}')
WEBAPP_URL = f"{APP_URL}/login.html"

# Проверка конфигурации
if not all([BOT_TOKEN, API_ID, API_HASH]):
    logger.error("Отсутствуют необходимые переменные окружения!")
    logger.error(f"BOT_TOKEN: {'Установлен' if BOT_TOKEN else 'Отсутствует'}")
    logger.error(f"API_ID: {'Установлен' if API_ID else 'Отсутствует'}")
    logger.error(f"API_HASH: {'Установлен' if API_HASH else 'Отсутствует'}")
    exit(1)

# Инициализация Flask
app = Flask(__name__, static_folder='docs')

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Хранилище сессий и клиентов
sessions = {}
telegram_clients = {}

# Маршруты Flask
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'login.html')

@app.route('/<path:path>')
def send_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/auth', methods=['POST'])
def auth():
    try:
        data = request.json
        if verify_telegram_data(data):
            user_id = str(data.get('id'))
            sessions[user_id] = {
                'auth_date': data.get('auth_date'),
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'username': data.get('username')
            }
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid auth data'})
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dialogs', methods=['GET'])
async def get_dialogs_route():
    try:
        user_id = request.args.get('user_id')
        if not user_id or user_id not in sessions:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        dialogs = await get_user_dialogs(user_id)
        return jsonify({'success': True, 'dialogs': dialogs})
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

async def init_telegram_client(user_id):
    """Инициализация клиента Telegram"""
    try:
        session_file = os.path.join('sessions', f'{user_id}.session')
        client = TelegramClient(session_file, API_ID, API_HASH)
        
        if not client.is_connected():
            await client.connect()
            logger.info(f"Клиент для пользователя {user_id} подключен")
            
        if not await client.is_user_authorized():
            logger.error(f"Пользователь {user_id} не авторизован в Telethon")
            raise Exception("Требуется авторизация в Telegram")
            
        return client
    except Exception as e:
        logger.error(f"Ошибка при инициализации клиента: {str(e)}")
        raise

async def get_user_dialogs(user_id):
    """Получение диалогов пользователя через Telethon"""
    try:
        if user_id not in telegram_clients:
            logger.info(f"Создаем новый клиент для пользователя {user_id}")
            client = await init_telegram_client(user_id)
            telegram_clients[user_id] = client
        
        client = telegram_clients[user_id]
        logger.info(f"Получаем диалоги для пользователя {user_id}")
        
        # Получаем диалоги
        dialogs = await client.get_dialogs()
        
        # Форматируем результат
        result = []
        for dialog in dialogs[:10]:
            try:
                entity = dialog.entity
                
                dialog_info = {
                    'id': entity.id,
                    'name': '',
                    'type': '',
                    'unread_count': dialog.unread_count,
                    'last_message': dialog.message.message if dialog.message else None,
                    'last_message_date': str(dialog.message.date) if dialog.message else None
                }
                
                if isinstance(entity, User):
                    dialog_info['name'] = f"{entity.first_name} {entity.last_name if entity.last_name else ''}"
                    dialog_info['type'] = 'user'
                elif isinstance(entity, Chat):
                    dialog_info['name'] = entity.title
                    dialog_info['type'] = 'chat'
                elif isinstance(entity, Channel):
                    dialog_info['name'] = entity.title
                    dialog_info['type'] = 'channel'
                    
                result.append(dialog_info)
            except Exception as e:
                logger.error(f"Ошибка при обработке диалога: {str(e)}")
                continue
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {str(e)}")
        raise

def verify_telegram_data(data):
    """Проверка подлинности данных от Telegram Login Widget"""
    try:
        if 'hash' not in data:
            logger.error("Отсутствует hash в данных авторизации")
            return False
        
        auth_data = data.copy()
        auth_hash = auth_data.pop('hash')
        
        # Проверяем срок действия авторизации
        auth_date = int(auth_data.get('auth_date', 0))
        if time.time() - auth_date > 86400:  # 24 часа
            logger.error("Срок действия авторизации истек")
            return False
        
        data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(auth_data.items())])
        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        
        hash_str = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hash_str == auth_hash
    except Exception as e:
        logger.error(f"Ошибка при проверке данных авторизации: {str(e)}")
        return False

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    """Обработчик команды /start"""
    try:
        logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(
            text="Открыть список диалогов",
            web_app=WebAppInfo(url=APP_URL)
        ))
        
        logger.info(f"Отправляем приветственное сообщение с APP_URL: {APP_URL}")
        await message.answer(
            "Привет! Это бот для просмотра диалогов Telegram.\n"
            "Нажмите на кнопку ниже, чтобы открыть приложение.",
            reply_markup=markup
        )
        logger.info("Приветственное сообщение отправлено успешно")
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при запуске бота. Попробуйте позже.")

def run_flask():
    """Запуск Flask сервера"""
    app.run(host=HOST, port=PORT)

def run_bot():
    """Запуск бота"""
    executor.start_polling(dp, skip_updates=True)

if __name__ == '__main__':
    # Создаем директорию для сессий, если её нет
    os.makedirs('sessions', exist_ok=True)
    
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Запускаем бота
    logger.info("🚀 Запуск бота и веб-сервера...")
    logger.info(f"Конфигурация:")
    logger.info(f"HOST: {HOST}")
    logger.info(f"PORT: {PORT}")
    logger.info(f"APP_URL: {APP_URL}")
    logger.info(f"WEBAPP_URL: {WEBAPP_URL}")
    
    run_bot() 