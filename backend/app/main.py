import os
import logging
import json
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

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
    
    try:
        # Получаем данные запроса
        update_data = await request.json()
        logger.info(f"Данные запроса: {update_data}")
        
        # Проверяем, есть ли сообщение в обновлении
        if 'message' in update_data:
            message = update_data['message']
            logger.info(f"Получено сообщение: {message}")
            
            # Проверяем, есть ли текст в сообщении
            if 'text' in message:
                text = message['text']
                logger.info(f"Текст сообщения: {text}")
                
                # Обрабатываем команду /start
                if text == '/start':
                    logger.info("Обрабатываем команду /start")
                    await handle_start_command(message)
                    return Response(content="OK", status_code=200)
        
        return Response(content="OK", status_code=200)
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}", exc_info=True)
        return Response(content="Error", status_code=500)

async def handle_start_command(message):
    """
    Обработчик команды /start
    """
    try:
        chat_id = message['chat']['id']
        user_first_name = message.get('from', {}).get('first_name', 'пользователь')
        user_id = message.get('from', {}).get('id')
        
        logger.info(f"Получена команда /start от пользователя {user_id} (имя: {user_first_name}, чат: {chat_id})")
        
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
        result = await send_telegram_message(
            chat_id=chat_id,
            text=f"Привет, {user_first_name}! Я бот для просмотра диалогов Telegram.",
            reply_markup=keyboard
        )
        
        logger.info(f"Результат отправки сообщения: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}", exc_info=True)
        return None

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
        logger.info(f"Отправка сообщения в чат {chat_id}: {text}")
        logger.info(f"URL запроса: {url}")
        logger.info(f"Данные запроса: {data}")
        
        response = await http_client.post(url, json=data)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Сообщение успешно отправлено в чат {chat_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}", exc_info=True)
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
        logger.info(f"Установка вебхука на {webhook_url}")
        response = await http_client.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Вебхук успешно установлен: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}", exc_info=True)
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
        logger.info("Удаление вебхука")
        response = await http_client.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Вебхук успешно удален: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука: {e}", exc_info=True)
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
    result = await set_telegram_webhook(webhook_url)
    
    # Проверяем, что вебхук установлен успешно
    if result and result.get("ok"):
        logger.info("Вебхук успешно установлен")
    else:
        logger.error(f"Не удалось установить вебхук: {result}")
    
    # Проверяем токен бота
    try:
        me_url = f"{TELEGRAM_API_URL}/getMe"
        response = await http_client.get(me_url)
        response.raise_for_status()
        me_data = response.json()
        if me_data.get("ok"):
            bot_info = me_data.get("result", {})
            logger.info(f"Бот успешно авторизован: @{bot_info.get('username')} ({bot_info.get('first_name')})")
        else:
            logger.error(f"Ошибка при получении информации о боте: {me_data}")
    except Exception as e:
        logger.error(f"Ошибка при проверке токена бота: {e}", exc_info=True)

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

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Корневой эндпоинт - возвращает HTML-страницу
    """
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
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