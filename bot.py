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
WEBAPP_URL = "https://askulibaba.github.io/enigma-telegram-app/login.html"

# Проверка конфигурации
if not all([BOT_TOKEN, API_ID, API_HASH]):
    logger.error("Отсутствуют необходимые переменные окружения!")
    logger.error(f"BOT_TOKEN: {'Установлен' if BOT_TOKEN else 'Отсутствует'}")
    logger.error(f"API_ID: {'Установлен' if API_ID else 'Отсутствует'}")
    logger.error(f"API_HASH: {'Установлен' if API_HASH else 'Отсутствует'}")
    exit(1)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Хранилище сессий и клиентов
sessions = {}
telegram_clients = {}

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
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {str(e)}")
        await message.answer("Произошла ошибка при запуске бота. Попробуйте позже.")

@dp.message_handler(content_types=['web_app_data'])
async def web_app_handler(message: types.Message):
    """Обработчик данных от веб-приложения"""
    try:
        logger.info(f"Получены данные от веб-приложения: {message.web_app_data.data}")
        data = json.loads(message.web_app_data.data)
        
        if data.get('type') == 'auth':
            auth_data = data.get('data', {})
            logger.info(f"Получены данные авторизации: {auth_data}")
            
            if verify_telegram_data(auth_data):
                user_id = str(auth_data.get('id'))
                sessions[user_id] = {
                    'auth_date': auth_data.get('auth_date'),
                    'first_name': auth_data.get('first_name'),
                    'last_name': auth_data.get('last_name'),
                    'username': auth_data.get('username')
                }
                
                try:
                    dialogs = await get_user_dialogs(user_id)
                    await message.answer("✅ Авторизация успешна!")
                    await message.answer(json.dumps(dialogs))
                except Exception as e:
                    logger.error(f"Ошибка при получении диалогов: {str(e)}")
                    await message.answer("❌ Ошибка при получении диалогов. Попробуйте позже.")
            else:
                logger.error("Ошибка проверки данных авторизации")
                await message.answer("❌ Ошибка авторизации: недействительные данные")
        
        elif data.get('type') == 'get_dialogs':
            user_id = str(message.from_user.id)
            if user_id in sessions:
                try:
                    dialogs = await get_user_dialogs(user_id)
                    await message.answer(json.dumps(dialogs))
                except Exception as e:
                    logger.error(f"Ошибка при получении диалогов: {str(e)}")
                    await message.answer("❌ Ошибка при получении диалогов. Попробуйте позже.")
            else:
                await message.answer("⚠️ Необходима авторизация")
                
        else:
            # Обработка зашифрованного текста
            user_id = str(message.from_user.id)
            if user_id in sessions:
                await message.answer(f"🔐 Зашифрованный текст: {data}")
            else:
                markup = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("Авторизоваться", web_app=WebAppInfo(url=WEBAPP_URL))
                )
                await message.answer(
                    "⚠️ Необходима авторизация для продолжения",
                    reply_markup=markup
                )
                
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {str(e)}")
        await message.answer("❌ Ошибка обработки данных: неверный формат")
    except Exception as e:
        logger.error(f"Необработанная ошибка: {str(e)}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

if __name__ == '__main__':
    # Создаем директорию для сессий, если её нет
    os.makedirs('sessions', exist_ok=True)
    logger.info("🚀 Запуск бота...")
    executor.start_polling(dp, skip_updates=True) 