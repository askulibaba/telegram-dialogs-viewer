import os
import logging
import json
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from app.core.config import settings
from app.api import auth, dialogs
from app.core.security import verify_token

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
    allow_origins=["*"],  # Разрешаем запросы с любых источников
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
        "drop_pending_updates": True,
        "allowed_updates": ["message", "callback_query"]
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

@app.get("/bot-info")
async def bot_info():
    """
    Получение информации о боте
    """
    try:
        me_url = f"{TELEGRAM_API_URL}/getMe"
        response = await http_client.get(me_url)
        response.raise_for_status()
        me_data = response.json()
        
        webhook_info_url = f"{TELEGRAM_API_URL}/getWebhookInfo"
        webhook_response = await http_client.get(webhook_info_url)
        webhook_response.raise_for_status()
        webhook_data = webhook_response.json()
        
        return JSONResponse({
            "bot_info": me_data,
            "webhook_info": webhook_data,
            "app_url": settings.APP_URL,
            "telegram_bot_token_prefix": settings.TELEGRAM_BOT_TOKEN[:10] + "..." if settings.TELEGRAM_BOT_TOKEN else None
        })
    except Exception as e:
        logger.error(f"Ошибка при получении информации о боте: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/send-test-message")
async def send_test_message(request: Request):
    """
    Отправка тестового сообщения
    """
    try:
        data = await request.json()
        chat_id = data.get("chat_id")
        
        if not chat_id:
            return JSONResponse({"error": "chat_id is required"}, status_code=400)
        
        result = await send_telegram_message(
            chat_id=chat_id,
            text="Это тестовое сообщение от бота Telegram Dialogs Viewer."
        )
        
        return JSONResponse({"result": result})
    except Exception as e:
        logger.error(f"Ошибка при отправке тестового сообщения: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/set-webhook")
async def set_webhook(request: Request):
    """
    Ручная установка вебхука
    """
    try:
        data = await request.json()
        webhook_url = data.get("webhook_url")
        
        if not webhook_url:
            webhook_url = f"{settings.APP_URL}/webhook"
        
        result = await set_telegram_webhook(webhook_url)
        
        return JSONResponse({"result": result})
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/delete-webhook")
async def delete_webhook():
    """
    Ручное удаление вебхука
    """
    try:
        result = await delete_telegram_webhook()
        
        return JSONResponse({"result": result})
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/v1/auth/manual")
async def manual_auth(request: Request):
    """
    Ручная авторизация для тестирования
    """
    try:
        data = await request.json()
        user_id = data.get("id")
        
        if not user_id:
            return JSONResponse({"error": "id is required"}, status_code=400)
        
        logger.info(f"Ручная авторизация для пользователя {user_id}")
        
        # Создаем тестовый токен
        access_token = f"test_token_{user_id}"
        
        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "first_name": data.get("first_name", "Test User"),
                "username": data.get("username", "test_user")
            }
        })
    except Exception as e:
        logger.error(f"Ошибка при ручной авторизации: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/v1/auth/telegram")
async def telegram_auth(request: Request):
    """
    Авторизация через Telegram Login Widget
    """
    try:
        data = await request.json()
        user_id = data.get("id")
        
        if not user_id:
            return JSONResponse({"error": "id is required"}, status_code=400)
        
        logger.info(f"Авторизация через Telegram для пользователя {user_id}")
        
        # Создаем тестовый токен
        access_token = f"telegram_token_{user_id}"
        
        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "username": data.get("username", ""),
                "photo_url": data.get("photo_url", "")
            }
        })
    except Exception as e:
        logger.error(f"Ошибка при авторизации через Telegram: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/v1/dialogs")
async def get_dialogs_direct(request: Request):
    """
    Прямой эндпоинт для получения диалогов (обходит проблему с CORS и Mixed Content)
    """
    logger.info("Прямой запрос диалогов")
    
    # Получаем токен из заголовка
    authorization = request.headers.get("Authorization")
    if not authorization:
        return JSONResponse({"error": "Не указан токен авторизации"}, status_code=401)
    
    try:
        # Проверяем формат токена
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return JSONResponse({"error": "Неверный формат токена"}, status_code=401)
        
        # Извлекаем ID пользователя из токена
        token_data = verify_token(token)
        if not token_data:
            return JSONResponse({"error": "Неверный токен авторизации"}, status_code=401)
        
        user_id = token_data.user_id
        logger.info(f"Получение диалогов для пользователя {user_id}")
        
        # Получаем параметры запроса
        force_refresh = request.query_params.get("force_refresh", "false").lower() == "true"
        
        # Преобразуем ID пользователя в целое число
        try:
            user_id_int = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать ID пользователя '{user_id}' в целое число")
            return JSONResponse({"error": "Неверный формат ID пользователя"}, status_code=400)
        
        # Получаем диалоги из Telegram
        try:
            from app.services.telegram import get_dialogs
            dialogs = await get_dialogs(user_id_int, force_refresh=force_refresh)
            logger.info(f"Получено {len(dialogs)} диалогов для пользователя {user_id}")
            return JSONResponse(dialogs)
        except ValueError as e:
            logger.error(f"Ошибка при получении диалогов: {e}")
            error_message = str(e)
            
            if "Превышен лимит запросов к API Telegram" in error_message:
                # Если превышен лимит запросов, возвращаем соответствующую ошибку
                return JSONResponse({"error": error_message}, status_code=429)
            elif "Аккаунт заблокирован Telegram" in error_message:
                # Если аккаунт заблокирован, возвращаем соответствующую ошибку
                return JSONResponse({"error": error_message}, status_code=403)
            elif "Сессия для пользователя" in error_message and "не найдена" in error_message:
                # Если сессия не найдена, возвращаем соответствующую ошибку
                return JSONResponse({"error": "Требуется авторизация в Telegram"}, status_code=401)
            else:
                # Возвращаем подробную информацию об ошибке
                return JSONResponse({"error": error_message}, status_code=400)
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса диалогов: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500) 