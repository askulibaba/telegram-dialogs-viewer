import os
import logging
import asyncio
from typing import Dict, List, Any, Optional
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from datetime import datetime, timedelta
import random

from app.core.config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Словарь для хранения клиентов
clients: Dict[int, TelegramClient] = {}


async def get_client(user_id: int) -> TelegramClient:
    """
    Получает или создает клиент Telegram для пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        TelegramClient: Клиент Telegram
    """
    if user_id in clients:
        return clients[user_id]
    
    # Создаем путь к файлу сессии
    session_file = os.path.join(settings.SESSIONS_DIR, f"user_{user_id}")
    
    # Создаем клиент
    client = TelegramClient(
        session_file,
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH
    )
    
    # Проверяем, авторизован ли клиент
    if not await client.is_user_authorized():
        raise ValueError("Пользователь не авторизован")
    
    # Сохраняем клиент
    clients[user_id] = client
    
    return client


async def send_code_request(phone_number: str) -> Dict[str, Any]:
    """
    Отправляет запрос на получение кода подтверждения
    
    Args:
        phone_number: Номер телефона
    
    Returns:
        Dict[str, Any]: Результат запроса
    """
    logger.info(f"Отправка кода на номер {phone_number}")
    
    # Заглушка для тестирования
    return {
        "temp_user_id": 123456789,
        "phone_code_hash": "test_hash",
        "phone_number": phone_number
    }


async def sign_in(
    temp_user_id: int,
    phone_number: str,
    code: str,
    phone_code_hash: str,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """
    Авторизация по коду подтверждения
    
    Args:
        temp_user_id: Временный ID пользователя
        phone_number: Номер телефона
        code: Код подтверждения
        phone_code_hash: Хеш кода подтверждения
        password: Пароль (опционально)
    
    Returns:
        Dict[str, Any]: Данные пользователя
    """
    logger.info(f"Авторизация по коду для номера {phone_number}")
    
    # Заглушка для тестирования
    return {
        "id": temp_user_id,
        "first_name": "Test",
        "last_name": "User",
        "username": "test_user",
        "phone": phone_number
    }


async def get_dialogs(user_id: str) -> List[Dict[str, Any]]:
    """
    Получает список диалогов пользователя
    
    Args:
        user_id: ID пользователя
    
    Returns:
        List[Dict[str, Any]]: Список диалогов
    """
    logger.info(f"Получение диалогов для пользователя {user_id}")
    
    # В реальном приложении здесь должен быть запрос к API Telegram
    # В данном случае возвращаем тестовые данные
    now = datetime.now()
    
    dialogs = [
        {
            "id": "1",
            "title": "Тестовый диалог 1",
            "last_message": "Привет! Как дела?",
            "last_message_date": now.isoformat(),
            "unread_count": 2
        },
        {
            "id": "2",
            "title": "Тестовый диалог 2",
            "last_message": "Посмотри это видео!",
            "last_message_date": (now - timedelta(days=1)).isoformat(),
            "unread_count": 0
        },
        {
            "id": "3",
            "title": "Тестовый диалог 3",
            "last_message": "Спасибо за информацию",
            "last_message_date": (now - timedelta(days=2)).isoformat(),
            "unread_count": 0
        }
    ]
    
    # Добавляем случайные диалоги
    for i in range(random.randint(1, 3)):
        dialogs.append({
            "id": str(100 + i),
            "title": f"Случайный диалог {i+1}",
            "last_message": f"Сообщение {random.randint(1, 100)}",
            "last_message_date": (now - timedelta(hours=random.randint(1, 24))).isoformat(),
            "unread_count": random.randint(0, 10)
        })
    
    return dialogs


async def get_messages(dialog_id: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Получает сообщения из диалога
    
    Args:
        dialog_id: ID диалога
        user_id: ID пользователя
    
    Returns:
        List[Dict[str, Any]]: Список сообщений
    """
    logger.info(f"Получение сообщений из диалога {dialog_id} для пользователя {user_id}")
    
    # В реальном приложении здесь должен быть запрос к API Telegram
    # В данном случае возвращаем тестовые данные
    now = datetime.now()
    
    messages = []
    for i in range(10):
        is_outgoing = random.choice([True, False])
        messages.append({
            "id": str(i + 1),
            "text": f"Тестовое сообщение {i + 1}",
            "date": (now - timedelta(minutes=i * 5)).isoformat(),
            "is_outgoing": is_outgoing,
            "sender": "Вы" if is_outgoing else f"Собеседник {dialog_id}"
        })
    
    return messages


async def send_message(dialog_id: str, text: str, user_id: str) -> Dict[str, Any]:
    """
    Отправляет сообщение в диалог
    
    Args:
        dialog_id: ID диалога
        text: Текст сообщения
        user_id: ID пользователя
    
    Returns:
        Dict[str, Any]: Результат отправки
    """
    logger.info(f"Отправка сообщения в диалог {dialog_id} от пользователя {user_id}: {text}")
    
    # В реальном приложении здесь должен быть запрос к API Telegram
    # В данном случае возвращаем тестовый результат
    return {
        "success": True,
        "message_id": str(random.randint(1000, 9999)),
        "date": datetime.now().isoformat()
    }


async def get_dialogs(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Получает список диалогов пользователя
    
    Args:
        user_id: ID пользователя
        limit: Максимальное количество диалогов
        
    Returns:
        List[Dict[str, Any]]: Список диалогов
    """
    # Получаем клиент
    client = await get_client(user_id)
    
    try:
        # Подключаемся к Telegram
        if not client.is_connected():
            await client.connect()
        
        # Получаем диалоги
        dialogs = await client.get_dialogs(limit=limit)
        
        # Форматируем результат
        result = []
        for dialog in dialogs:
            entity = dialog.entity
            
            # Определяем тип диалога
            dialog_type = "user"
            if hasattr(entity, "megagroup") and entity.megagroup:
                dialog_type = "group"
            elif hasattr(entity, "broadcast") and entity.broadcast:
                dialog_type = "channel"
            elif hasattr(entity, "gigagroup") and entity.gigagroup:
                dialog_type = "supergroup"
            
            # Получаем имя диалога
            name = ""
            if hasattr(entity, "title"):
                name = entity.title
            elif hasattr(entity, "first_name"):
                name = entity.first_name
                if hasattr(entity, "last_name") and entity.last_name:
                    name += f" {entity.last_name}"
            
            # Получаем фото диалога
            photo_url = None
            if hasattr(entity, "photo") and entity.photo:
                try:
                    photo = await client.download_profile_photo(entity, bytes)
                    if photo:
                        # Здесь можно сохранить фото и вернуть URL
                        pass
                except Exception as e:
                    logger.error(f"Ошибка при загрузке фото: {str(e)}")
            
            # Добавляем диалог в результат
            result.append({
                "id": dialog.id,
                "name": name,
                "type": dialog_type,
                "unread_count": dialog.unread_count,
                "last_message": {
                    "text": dialog.message.message if dialog.message else "",
                    "date": dialog.message.date.isoformat() if dialog.message else None
                },
                "photo_url": photo_url
            })
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {str(e)}")
        raise


async def get_messages(user_id: int, dialog_id: int, limit: int = 20, offset_id: int = 0) -> List[Dict[str, Any]]:
    """
    Получает сообщения из диалога
    
    Args:
        user_id: ID пользователя
        dialog_id: ID диалога
        limit: Максимальное количество сообщений
        offset_id: ID сообщения, с которого начинать
        
    Returns:
        List[Dict[str, Any]]: Список сообщений
    """
    # Получаем клиент
    client = await get_client(user_id)
    
    try:
        # Подключаемся к Telegram
        if not client.is_connected():
            await client.connect()
        
        # Получаем сообщения
        messages = await client.get_messages(
            dialog_id,
            limit=limit,
            offset_id=offset_id
        )
        
        # Форматируем результат
        result = []
        for message in messages:
            # Добавляем сообщение в результат
            result.append({
                "id": message.id,
                "text": message.message,
                "date": message.date.isoformat(),
                "out": message.out,
                "reply_to_msg_id": message.reply_to_msg_id,
                "from_id": message.from_id.user_id if message.from_id else None
            })
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений: {str(e)}")
        raise


async def send_message(user_id: int, dialog_id: int, text: str, reply_to: Optional[int] = None) -> Dict[str, Any]:
    """
    Отправляет сообщение в диалог
    
    Args:
        user_id: ID пользователя
        dialog_id: ID диалога
        text: Текст сообщения
        reply_to: ID сообщения, на которое отвечаем
        
    Returns:
        Dict[str, Any]: Информация о отправленном сообщении
    """
    # Получаем клиент
    client = await get_client(user_id)
    
    try:
        # Подключаемся к Telegram
        if not client.is_connected():
            await client.connect()
        
        # Отправляем сообщение
        message = await client.send_message(
            dialog_id,
            text,
            reply_to=reply_to
        )
        
        # Форматируем результат
        result = {
            "id": message.id,
            "text": message.message,
            "date": message.date.isoformat(),
            "out": message.out
        }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {str(e)}")
        raise 