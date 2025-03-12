import os
import logging
import json
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

# Базовый URL для Telegram Bot API
TELEGRAM_API_URL = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"

# HTTP клиент
http_client = httpx.AsyncClient()

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
    
    # Проверяем, есть ли сообщение в обновлении
    if 'message' in update_data:
        message = update_data['message']
        
        # Проверяем, есть ли текст в сообщении
        if 'text' in message:
            text = message['text']
            
            # Обрабатываем команду /start
            if text == '/start':
                await handle_start_command(message)
    
    return Response()

async def handle_start_command(message):
    """
    Обработчик команды /start
    """
    chat_id = message['chat']['id']
    user_first_name = message.get('from', {}).get('first_name', 'пользователь')
    user_id = message.get('from', {}).get('id')
    
    logger.info(f"Получена команда /start от пользователя {user_id}")
    
    # Создаем кнопку для открытия веб-приложения
    keyboard = {
        'inline_keyboard': [
            [
                {
                    'text': 'Открыть приложение',
                    'web_app': {
                        'url': settings.APP_URL
                    }
                }
            ]
        ]
    }
    
    # Отправляем приветственное сообщение
    await send_telegram_message(
        chat_id=chat_id,
        text=f"Привет, {user_first_name}! Я бот для просмотра диалогов Telegram.",
        reply_markup=keyboard
    )

async def send_telegram_message(chat_id, text, reply_markup=None):
    """
    Отправляет сообщение через Telegram API
    
    Args:
        chat_id: ID чата
        text: Текст сообщения
        reply_markup: Клавиатура (опционально)
    """
    url = f"{TELEGRAM_API_URL}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": text
    }
    
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = await http_client.post(url, json=data)
        response.raise_for_status()
        logger.info(f"Сообщение успешно отправлено в чат {chat_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        return None

async def set_telegram_webhook(webhook_url):
    """
    Устанавливает вебхук для Telegram бота
    
    Args:
        webhook_url: URL вебхука
    """
    url = f"{TELEGRAM_API_URL}/setWebhook"
    
    data = {
        "url": webhook_url,
        "drop_pending_updates": True
    }
    
    try:
        response = await http_client.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Вебхук успешно установлен: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}")
        return None

async def delete_telegram_webhook():
    """
    Удаляет вебхук для Telegram бота
    """
    url = f"{TELEGRAM_API_URL}/deleteWebhook"
    
    data = {
        "drop_pending_updates": True
    }
    
    try:
        response = await http_client.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Вебхук успешно удален: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука: {e}")
        return None

@app.on_event("startup")
async def on_startup():
    """
    Действия при запуске приложения
    """
    logger.info("Запуск приложения...")
    
    # Удаляем все предыдущие вебхуки
    await delete_telegram_webhook()
    
    # Формируем URL вебхука
    webhook_url = f"{settings.APP_URL}/webhook"
    
    # Устанавливаем вебхук
    await set_telegram_webhook(webhook_url)

@app.on_event("shutdown")
async def on_shutdown():
    """
    Действия при остановке приложения
    """
    logger.info("Остановка приложения...")
    
    # Удаляем вебхук
    await delete_telegram_webhook()
    
    # Закрываем HTTP клиент
    await http_client.aclose()
    logger.info("HTTP клиент закрыт")

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