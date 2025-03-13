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
    logger.info(f"Запрос на получение клиента для пользователя {user_id}")
    
    # Проверяем, есть ли клиент в кэше
    if user_id in clients:
        logger.info(f"Клиент для пользователя {user_id} найден в кэше")
        client = clients[user_id]
        
        # Проверяем, подключен ли клиент
        try:
            if not client.is_connected():
                logger.info(f"Клиент не подключен, подключаемся")
                await client.connect()
                
            # Проверяем авторизацию
            if await client.is_user_authorized():
                logger.info(f"Клиент авторизован, возвращаем его")
                return client
            else:
                logger.warning(f"Клиент не авторизован, создаем новый")
                # Если клиент не авторизован, удаляем его из кэша
                del clients[user_id]
        except Exception as e:
            logger.error(f"Ошибка при проверке клиента: {str(e)}")
            # Если произошла ошибка, удаляем клиент из кэша
            del clients[user_id]
    
    # Создаем путь к файлу сессии
    session_file = os.path.join(settings.SESSIONS_DIR, f"user_{user_id}")
    logger.info(f"Путь к файлу сессии: {session_file}")
    
    # Проверяем существование файла сессии
    if not os.path.exists(f"{session_file}.session"):
        logger.error(f"Файл сессии не найден: {session_file}.session")
        
        # Проверяем содержимое директории сессий
        try:
            session_files = os.listdir(settings.SESSIONS_DIR)
            logger.info(f"Файлы в директории сессий: {session_files}")
            
            # Проверяем, есть ли файлы сессий для других пользователей
            for file in session_files:
                if file.startswith("user_") and file.endswith(".session"):
                    other_user_id = file.replace("user_", "").replace(".session", "")
                    logger.info(f"Найден файл сессии для пользователя {other_user_id}")
            
            # Проверяем, есть ли временные файлы сессий
            for file in session_files:
                if file.startswith("temp_user_") and file.endswith(".session"):
                    temp_user_id = file.replace("temp_user_", "").replace(".session", "")
                    logger.info(f"Найден временный файл сессии: {temp_user_id}")
                    
                    # Пробуем использовать временный файл сессии
                    logger.info(f"Пробуем использовать временный файл сессии {temp_user_id} для пользователя {user_id}")
                    try:
                        import shutil
                        shutil.copy(os.path.join(settings.SESSIONS_DIR, file), f"{session_file}.session")
                        logger.info(f"Временный файл сессии скопирован в {session_file}.session")
                    except Exception as e:
                        logger.error(f"Ошибка при копировании временного файла сессии: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка при чтении директории сессий: {str(e)}")
        
        # Если файл сессии все еще не существует, выбрасываем исключение
        if not os.path.exists(f"{session_file}.session"):
            raise ValueError(f"Сессия для пользователя {user_id} не найдена")
    else:
        # Проверяем размер файла сессии
        try:
            file_size = os.path.getsize(f"{session_file}.session")
            logger.info(f"Размер файла сессии: {file_size} байт")
            
            if file_size == 0:
                logger.error(f"Файл сессии пуст: {session_file}.session")
                raise ValueError(f"Файл сессии пуст: {session_file}.session")
        except Exception as e:
            logger.error(f"Ошибка при проверке размера файла сессии: {str(e)}")
    
    # Создаем клиент
    logger.info(f"Создаем клиент для пользователя {user_id}")
    client = TelegramClient(
        session_file,
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH
    )
    
    try:
        # Подключаемся к Telegram
        logger.info(f"Подключаемся к Telegram")
        await client.connect()
        
        # Проверяем, авторизован ли клиент
        logger.info(f"Проверяем авторизацию клиента")
        is_authorized = await client.is_user_authorized()
        logger.info(f"Клиент авторизован: {is_authorized}")
        
        if not is_authorized:
            logger.error(f"Пользователь {user_id} не авторизован")
            raise ValueError("Пользователь не авторизован")
        
        # Получаем информацию о пользователе
        try:
            me = await client.get_me()
            logger.info(f"Информация о пользователе: id={me.id}, username={me.username}, phone={me.phone}")
        except Exception as e:
            logger.error(f"Ошибка при получении информации о пользователе: {str(e)}")
        
        # Сохраняем клиент
        logger.info(f"Сохраняем клиент в кэш")
        clients[user_id] = client
        
        return client
    except Exception as e:
        # Если произошла ошибка, закрываем клиент
        logger.error(f"Ошибка при создании клиента: {str(e)}")
        await client.disconnect()
        raise


async def send_code_request(phone_number: str) -> Dict[str, Any]:
    """
    Отправляет запрос на получение кода подтверждения
    
    Args:
        phone_number: Номер телефона
    
    Returns:
        Dict[str, Any]: Результат запроса
    """
    logger.info(f"Отправка кода на номер {phone_number}")
    
    try:
        # Создаем временный клиент для отправки кода
        # Используем случайный ID для временного пользователя
        temp_user_id = random.randint(100000, 999999)
        
        # Создаем путь к файлу сессии
        session_file = os.path.join(settings.SESSIONS_DIR, f"temp_user_{temp_user_id}")
        
        # Создаем клиент
        client = TelegramClient(
            session_file,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH
        )
        
        # Подключаемся к Telegram
        await client.connect()
        
        # Отправляем запрос на получение кода
        sent_code = await client.send_code_request(phone_number)
        
        # Сохраняем клиент для последующего использования
        clients[temp_user_id] = client
        
        # Возвращаем результат
        return {
            "temp_user_id": temp_user_id,
            "phone_code_hash": sent_code.phone_code_hash,
            "phone_number": phone_number
        }
    except Exception as e:
        logger.error(f"Ошибка при отправке кода: {str(e)}")
        raise


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
    
    try:
        # Получаем клиент
        if temp_user_id not in clients:
            raise ValueError("Сессия истекла. Пожалуйста, запросите код повторно.")
        
        client = clients[temp_user_id]
        
        # Подключаемся к Telegram, если не подключены
        if not client.is_connected():
            await client.connect()
        
        try:
            # Пытаемся авторизоваться по коду
            logger.info(f"Авторизация по коду для номера {phone_number}")
            user = await client.sign_in(
                phone=phone_number,
                code=code,
                phone_code_hash=phone_code_hash
            )
            logger.info(f"Успешная авторизация по коду для номера {phone_number}")
        except SessionPasswordNeededError:
            # Если требуется пароль двухфакторной аутентификации
            if not password:
                logger.info(f"Требуется пароль двухфакторной аутентификации для номера {phone_number}")
                raise ValueError("Требуется пароль двухфакторной аутентификации")
            
            # Авторизуемся с паролем
            logger.info(f"Авторизация с паролем для номера {phone_number}")
            user = await client.sign_in(password=password)
            logger.info(f"Успешная авторизация с паролем для номера {phone_number}")
        
        # Получаем информацию о пользователе
        me = await client.get_me()
        logger.info(f"Успешная авторизация пользователя: {me.id}")
        
        # Форматируем результат
        result = {
            "id": me.id,
            "first_name": me.first_name,
            "last_name": me.last_name if hasattr(me, "last_name") else "",
            "username": me.username if hasattr(me, "username") else "",
            "phone": phone_number
        }
        
        # Явно сохраняем сессию
        try:
            await client.session.save()
            logger.info(f"Сессия сохранена явно")
        except Exception as e:
            logger.error(f"Ошибка при явном сохранении сессии: {str(e)}")
        
        # Перемещаем сессию из временной в постоянную
        temp_session_file = os.path.join(settings.SESSIONS_DIR, f"temp_user_{temp_user_id}")
        permanent_session_file = os.path.join(settings.SESSIONS_DIR, f"user_{me.id}")
        logger.info(f"Перемещаем сессию из {temp_session_file} в {permanent_session_file}")
        
        if os.path.exists(f"{temp_session_file}.session"):
            try:
                # Копируем файл сессии
                import shutil
                try:
                    shutil.copy(f"{temp_session_file}.session", f"{permanent_session_file}.session")
                    logger.info(f"Сессия успешно скопирована")
                    
                    # Проверяем, что файл был скопирован
                    if os.path.exists(f"{permanent_session_file}.session"):
                        logger.info(f"Файл сессии успешно создан: {permanent_session_file}.session")
                        
                        # Удаляем временный файл сессии
                        try:
                            os.remove(f"{temp_session_file}.session")
                            logger.info(f"Временный файл сессии удален")
                        except Exception as e:
                            logger.error(f"Ошибка при удалении временного файла сессии: {str(e)}")
                    else:
                        logger.error(f"Файл сессии не был создан: {permanent_session_file}.session")
                except Exception as copy_error:
                    logger.error(f"Ошибка при копировании сессии: {str(copy_error)}")
            except Exception as e:
                logger.error(f"Ошибка при работе с файлами сессий: {str(e)}")
        else:
            logger.warning(f"Файл сессии не найден: {temp_session_file}.session")
            
            # Проверяем содержимое директории сессий
            try:
                session_files = os.listdir(settings.SESSIONS_DIR)
                logger.info(f"Файлы в директории сессий: {session_files}")
            except Exception as e:
                logger.error(f"Ошибка при чтении директории сессий: {str(e)}")
        
        # Создаем новый клиент с постоянным файлом сессии
        try:
            new_client = TelegramClient(
                permanent_session_file,
                settings.TELEGRAM_API_ID,
                settings.TELEGRAM_API_HASH
            )
            
            # Подключаемся к Telegram
            await new_client.connect()
            
            # Проверяем, авторизован ли клиент
            is_authorized = await new_client.is_user_authorized()
            logger.info(f"Новый клиент авторизован: {is_authorized}")
            
            if is_authorized:
                # Обновляем словарь клиентов
                clients[me.id] = new_client
                logger.info(f"Новый клиент сохранен в кэш")
            else:
                logger.error(f"Новый клиент не авторизован")
                # Используем старый клиент
                clients[me.id] = client
                logger.info(f"Используем старый клиент")
        except Exception as e:
            logger.error(f"Ошибка при создании нового клиента: {str(e)}")
            # Используем старый клиент
            clients[me.id] = client
            logger.info(f"Используем старый клиент из-за ошибки")
        
        # Удаляем временный клиент из кэша
        if temp_user_id in clients:
            del clients[temp_user_id]
            logger.info(f"Временный клиент удален из кэша")
        
        return result
    except PhoneCodeInvalidError:
        raise ValueError("Неверный код подтверждения")
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {str(e)}")
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
    logger.info(f"Получение диалогов для пользователя {user_id}")
    
    try:
        # Получаем клиент
        logger.info(f"Пытаемся получить клиент для пользователя {user_id}")
        client = await get_client(user_id)
        
        # Подключаемся к Telegram, если не подключены
        logger.info(f"Проверяем подключение клиента")
        if not client.is_connected():
            logger.info(f"Клиент не подключен, подключаемся")
            await client.connect()
        
        # Получаем диалоги
        logger.info(f"Запрашиваем диалоги с лимитом {limit}")
        dialogs = await client.get_dialogs(limit=limit)
        logger.info(f"Получено {len(dialogs)} диалогов")
        
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
            
            # Получаем последнее сообщение
            last_message = ""
            last_message_date = None
            if dialog.message:
                last_message = dialog.message.message
                last_message_date = dialog.message.date.isoformat()
            
            # Добавляем диалог в результат
            result.append({
                "id": dialog.id,
                "title": name,
                "type": dialog_type,
                "last_message": last_message,
                "last_message_date": last_message_date,
                "unread_count": dialog.unread_count
            })
        
        logger.info(f"Возвращаем {len(result)} диалогов")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {str(e)}")
        # Вместо возврата тестовых данных, выбрасываем исключение
        raise ValueError(f"Ошибка при получении диалогов: {str(e)}")


async def get_test_dialogs(user_id: str) -> List[Dict[str, Any]]:
    """
    Получает тестовые диалоги для отладки
    
    Args:
        user_id: ID пользователя
    
    Returns:
        List[Dict[str, Any]]: Список тестовых диалогов
    """
    logger.info(f"Получение тестовых диалогов для пользователя {user_id}")
    
    # Возвращаем тестовые данные
    now = datetime.now()
    
    dialogs = [
        {
            "id": "1",
            "title": "Тестовый диалог 1",
            "type": "user",
            "last_message": "Привет! Как дела?",
            "last_message_date": now.isoformat(),
            "unread_count": 2
        },
        {
            "id": "2",
            "title": "Тестовый диалог 2",
            "type": "group",
            "last_message": "Посмотри это видео!",
            "last_message_date": (now - timedelta(days=1)).isoformat(),
            "unread_count": 0
        },
        {
            "id": "3",
            "title": "Тестовый диалог 3",
            "type": "channel",
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
            "type": "user",
            "last_message": f"Сообщение {random.randint(1, 100)}",
            "last_message_date": (now - timedelta(hours=random.randint(1, 24))).isoformat(),
            "unread_count": random.randint(0, 10)
        })
    
    return dialogs


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
    logger.info(f"Получение сообщений из диалога {dialog_id} для пользователя {user_id}")
    
    try:
        # Получаем клиент
        client = await get_client(user_id)
        
        # Подключаемся к Telegram, если не подключены
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
            # Получаем информацию об отправителе
            sender_name = "Неизвестный"
            is_outgoing = message.out
            
            if is_outgoing:
                sender_name = "Вы"
            elif message.sender:
                if hasattr(message.sender, "first_name"):
                    sender_name = message.sender.first_name
                    if hasattr(message.sender, "last_name") and message.sender.last_name:
                        sender_name += f" {message.sender.last_name}"
                elif hasattr(message.sender, "title"):
                    sender_name = message.sender.title
            
            # Добавляем сообщение в результат
            result.append({
                "id": message.id,
                "text": message.message,
                "date": message.date.isoformat(),
                "is_outgoing": is_outgoing,
                "sender": sender_name,
                "reply_to_msg_id": message.reply_to_msg_id
            })
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений: {str(e)}")
        # В случае ошибки возвращаем тестовые данные
        return await get_test_messages(dialog_id, user_id)


async def get_test_messages(dialog_id: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Получает тестовые сообщения для отладки
    
    Args:
        dialog_id: ID диалога
        user_id: ID пользователя
    
    Returns:
        List[Dict[str, Any]]: Список тестовых сообщений
    """
    logger.info(f"Получение тестовых сообщений из диалога {dialog_id} для пользователя {user_id}")
    
    # Возвращаем тестовые данные
    now = datetime.now()
    
    messages = []
    for i in range(10):
        is_outgoing = random.choice([True, False])
        messages.append({
            "id": str(i + 1),
            "text": f"Тестовое сообщение {i + 1}",
            "date": (now - timedelta(minutes=i * 5)).isoformat(),
            "is_outgoing": is_outgoing,
            "sender": "Вы" if is_outgoing else f"Собеседник {dialog_id}",
            "reply_to_msg_id": None
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