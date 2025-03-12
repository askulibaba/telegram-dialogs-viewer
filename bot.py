import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from bot.utils import init_telegram_client, get_dialogs, verify_telegram_auth

# Загружаем переменные окружения
load_dotenv()

# Настройка уровня логирования в зависимости от переменной DEBUG
debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
log_level = logging.DEBUG if debug_mode else logging.INFO

# Настройка логирования
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if debug_mode:
    logger.debug("🔍 Режим отладки включен")

# Проверка конфигурации
required_vars = ['BOT_TOKEN', 'API_ID', 'API_HASH', 'APP_URL']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Отсутствуют необходимые переменные окружения: {', '.join(missing_vars)}")
    logger.error("Пожалуйста, добавьте их в настройках проекта на Railway или в файл .env")

# Создаем директорию для сессий, если она не существует
os.makedirs('sessions', exist_ok=True)

# Инициализация бота
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher(bot)

# Хранилище для клиентов
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
        
        # Также добавим инлайн-кнопку для открытия веб-приложения
        inline_markup = InlineKeyboardMarkup()
        inline_markup.add(InlineKeyboardButton(
            text="Открыть в браузере",
            url=os.getenv('APP_URL')
        ))
        
        await message.answer(
            "Привет! Это бот для просмотра диалогов Telegram.\n"
            "Нажмите на кнопку ниже, чтобы открыть приложение.",
            reply_markup=markup
        )
        
        await message.answer(
            "Или вы можете открыть приложение в браузере:",
            reply_markup=inline_markup
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
        logger.info(f"Данные: {data}")
        
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
        
        # Отправляем информацию о диалогах
        if dialogs:
            dialog_text = "Ваши последние диалоги:\n\n"
            for i, dialog in enumerate(dialogs[:10], 1):
                unread = f" (непрочитано: {dialog['unread_count']})" if dialog['unread_count'] > 0 else ""
                last_msg = f"\nПоследнее сообщение: {dialog['last_message'][:30]}..." if dialog['last_message'] else ""
                dialog_text += f"{i}. {dialog['name']}{unread}{last_msg}\n\n"
            
            await message.answer(dialog_text)
        else:
            await message.answer("Диалоги не найдены.")
        
        logger.info(f"Успешно получены и отправлены диалоги для пользователя {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке данных веб-приложения: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при обработке данных. Попробуйте позже.")

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(
        "Этот бот позволяет просматривать ваши диалоги в Telegram.\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n\n"
        "Для просмотра диалогов нажмите на кнопку 'Открыть список диалогов'."
    )

@dp.message_handler()
async def echo(message: types.Message):
    """Обработчик всех остальных сообщений"""
    await message.answer(
        "Я не понимаю эту команду. Используйте /start для начала работы или /help для получения справки."
    )

async def main():
    """Основная функция запуска бота"""
    try:
        logger.info("🚀 Запуск бота...")
        logger.info(f"Конфигурация:")
        logger.info(f"APP_URL: {os.getenv('APP_URL')}")
        logger.info(f"Режим отладки: {'Включен' if debug_mode else 'Выключен'}")
        
        # Запускаем бота
        await dp.start_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}", exc_info=True)

if __name__ == '__main__':
    # Запускаем бота
    asyncio.run(main()) 