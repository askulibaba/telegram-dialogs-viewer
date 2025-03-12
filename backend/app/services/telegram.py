import os
import logging
import asyncio
from typing import Dict, List, Any, Optional
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

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
    Отправляет запрос на код подтверждения
    
    Args:
        phone_number: Номер телефона
        
    Returns:
        Dict[str, Any]: Результат запроса
    """
    # Генерируем временный ID пользователя
    temp_user_id = abs(hash(phone_number)) % 10000000
    
    # Создаем путь к файлу сессии
    session_file = os.path.join(settings.SESSIONS_DIR, f"user_{temp_user_id}")
    
    # Создаем клиент
    client = TelegramClient(
        session_file,
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH
    )
    
    try:
        # Подключаемся к Telegram
        await client.connect()
        
        # Отправляем запрос на код
        result = await client.send_code_request(phone_number)
        
        # Сохраняем клиент
        clients[temp_user_id] = client
        
        return {
            "temp_user_id": temp_user_id,
            "phone_code_hash": result.phone_code_hash
        }
    except Exception as e:
        logger.error(f"Ошибка при отправке кода: {str(e)}")
        if client.is_connected():
            await client.disconnect()
        raise


async def sign_in(temp_user_id: int, phone_number: str, code: str, 
                 phone_code_hash: str, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Авторизует пользователя по коду
    
    Args:
        temp_user_id: Временный ID пользователя
        phone_number: Номер телефона
        code: Код подтверждения
        phone_code_hash: Хеш кода
        password: Пароль двухфакторной аутентификации
        
    Returns:
        Dict[str, Any]: Информация о пользователе
    """
    # Получаем клиент
    if temp_user_id not in clients:
        raise ValueError("Сессия не найдена")
    
    client = clients[temp_user_id]
    
    try:
        # Подключаемся к Telegram
        if not client.is_connected():
            await client.connect()
        
        # Авторизуемся по коду
        try:
            user = await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            # Если требуется пароль двухфакторной аутентификации
            if not password:
                raise ValueError("Требуется пароль двухфакторной аутентификации")
            
            user = await client.sign_in(password=password)
        except PhoneCodeInvalidError:
            raise ValueError("Неверный код подтверждения")
        
        # Получаем информацию о пользователе
        me = await client.get_me()
        
        # Переименовываем файл сессии
        old_session_file = os.path.join(settings.SESSIONS_DIR, f"user_{temp_user_id}")
        new_session_file = os.path.join(settings.SESSIONS_DIR, f"user_{me.id}")
        
        # Закрываем клиент
        await client.disconnect()
        
        # Удаляем клиент из словаря
        del clients[temp_user_id]
        
        # Переименовываем файл сессии
        if os.path.exists(f"{old_session_file}.session"):
            os.rename(f"{old_session_file}.session", f"{new_session_file}.session")
        
        # Создаем новый клиент
        new_client = TelegramClient(
            new_session_file,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH
        )
        
        # Подключаемся к Telegram
        await new_client.connect()
        
        # Сохраняем клиент
        clients[me.id] = new_client
        
        return {
            "id": me.id,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "phone": me.phone
        }
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {str(e)}")
        if client.is_connected():
            await client.disconnect()
        raise


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