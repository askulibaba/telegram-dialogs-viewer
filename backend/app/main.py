import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.webhook import SendMessage

from app.core.config import settings
from app.api import auth, dialogs

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем приложение FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Настраиваем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["auth"]
)
app.include_router(
    dialogs.router,
    prefix=f"{settings.API_V1_STR}/dialogs",
    tags=["dialogs"]
)

# Проверяем, существует ли директория для статических файлов
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # Подключаем статические файлы
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Создаем бота и диспетчер
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """
    Обработчик команды /start
    """
    logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
    
    # Создаем кнопку для открытия веб-приложения
    webapp_button = types.InlineKeyboardButton(
        text="Открыть приложение",
        web_app=types.WebAppInfo(url=settings.APP_URL)
    )
    keyboard = types.InlineKeyboardMarkup().add(webapp_button)
    
    # Отправляем приветственное сообщение
    return SendMessage(
        chat_id=message.chat.id,
        text=f"Привет, {message.from_user.first_name}! Я бот для просмотра диалогов Telegram.",
        reply_markup=keyboard
    )

# Эндпоинт для вебхука Telegram
@app.post("/webhook")
async def webhook(request: Request):
    """
    Обработчик вебхука Telegram
    """
    logger.info("Получен запрос на вебхук")
    
    # Получаем данные запроса
    update_data = await request.json()
    logger.info(f"Данные запроса: {update_data}")
    
    # Создаем объект Update
    update = types.Update(**update_data)
    
    # Обрабатываем обновление
    results = await dp.process_update(update)
    
    # Если есть результаты, отправляем их
    if results:
        return results[0]
    
    return Response()

@app.on_event("startup")
async def on_startup():
    """
    Действия при запуске приложения
    """
    logger.info("Запуск приложения...")
    
    # Удаляем все предыдущие вебхуки
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Предыдущие вебхуки удалены")
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука: {e}")
    
    # Формируем URL вебхука
    webhook_url = f"{settings.APP_URL}/webhook"
    
    # Устанавливаем вебхук
    try:
        logger.info(f"Устанавливаем вебхук на {webhook_url}")
        await bot.set_webhook(webhook_url)
        logger.info("Вебхук успешно установлен")
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    """
    Действия при остановке приложения
    """
    logger.info("Остановка приложения...")
    
    # Удаляем вебхук
    try:
        await bot.delete_webhook()
        logger.info("Вебхук удален")
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука: {e}")
    
    # Закрываем сессию бота
    await bot.session.close()
    logger.info("Сессия бота закрыта")

@app.get("/")
async def root():
    """
    Корневой эндпоинт
    """
    return {
        "app_name": settings.APP_NAME,
        "version": "0.1.0",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health():
    """
    Проверка работоспособности
    """
    return {"status": "ok"} 