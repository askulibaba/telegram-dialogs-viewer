import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from dotenv import load_dotenv
from .utils import init_telegram_client, get_dialogs, verify_telegram_auth

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher(bot)

# Хранилище для клиентов Telegram
telegram_clients = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    """Обработчик команды /start"""
    try:
        logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
        
        # Создаем клавиатуру с кнопкой для открытия веб-приложения
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(
            text="Открыть список диалогов",
            web_app=WebAppInfo(url=os.getenv('APP_URL'))
        ))
        
        await message.answer(
            "Привет! Это бот для просмотра диалогов Telegram.\n"
            "Нажмите на кнопку ниже, чтобы открыть приложение.",
            reply_markup=markup
        )
        logger.info("Приветственное сообщение отправлено успешно")
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при запуске бота. Попробуйте позже.")

@dp.message_handler(content_types=['web_app_data'])
async def web_app_data_handler(message: types.Message):
    """Обработчик данных от веб-приложения"""
    try:
        logger.info(f"Получены данные от веб-приложения от пользователя {message.from_user.id}")
        data = message.web_app_data.data
        
        # Проверяем данные авторизации
        if not verify_telegram_auth(os.getenv('BOT_TOKEN'), data):
            logger.error("Ошибка верификации данных авторизации")
            await message.answer("Ошибка авторизации. Попробуйте снова.")
            return
            
        # Инициализируем клиент Telegram
        client = await init_telegram_client(
            str(message.from_user.id),
            os.getenv('API_ID'),
            os.getenv('API_HASH')
        )
        telegram_clients[str(message.from_user.id)] = client
        
        # Получаем диалоги
        dialogs = await get_dialogs(client)
        
        await message.answer("Авторизация успешна! Ваши диалоги загружены.")
        logger.info(f"Успешно получены диалоги для пользователя {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке данных веб-приложения: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при обработке данных. Попробуйте позже.") 