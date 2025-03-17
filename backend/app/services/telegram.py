import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError, UserDeactivatedBanError
from datetime import datetime, timedelta
import random
import time

from app.core.config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Словарь для хранения клиентов
clients: Dict[int, TelegramClient] = {}

# Словарь для отслеживания времени последнего запроса
last_request_time: Dict[int, float] = {}

# Кэш диалогов: user_id -> (dialogs, timestamp)
dialogs_cache: Dict[int, Tuple[List[Dict[str, Any]], float]] = {}

# Кэш сообщений: (user_id, dialog_id) -> (messages, timestamp)
messages_cache: Dict[Tuple[int, int], Tuple[List[Dict[str, Any]], float]] = {}

# Минимальный интервал между запросами (в секундах)
MIN_REQUEST_INTERVAL = 0.1

# Время жизни кэша (в секундах)
CACHE_TTL = 3600.0  # 1 час

def ensure_sessions_dir():
    """
    Проверяет и создает директорию для сессий, если она не существует.
    Также проверяет права на запись.
    
    Returns:
        bool: True, если директория существует и доступна для записи, иначе False
    """
    try:
        # Проверяем существование директории сессий
        if not os.path.exists(settings.SESSIONS_DIR):
            try:
                os.makedirs(settings.SESSIONS_DIR, exist_ok=True)
                logger.info(f"Создана директория сессий: {settings.SESSIONS_DIR}")
            except Exception as e:
                logger.error(f"Ошибка при создании директории сессий: {str(e)}")
                return False
        
        # Проверяем права на запись в директорию сессий
        try:
            test_file = os.path.join(settings.SESSIONS_DIR, "test_write_permission.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            logger.info(f"Проверка прав на запись в директорию сессий успешна")
            return True
        except Exception as e:
            logger.error(f"Нет прав на запись в директорию сессий: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при проверке директории сессий: {str(e)}")
        return False

# Проверяем директорию сессий при запуске
sessions_dir_writable = ensure_sessions_dir()
logger.info(f"Директория сессий доступна для записи: {sessions_dir_writable}")
if settings.IS_RAILWAY:
    logger.info(f"Приложение запущено на Railway. Путь к сессиям: {settings.SESSIONS_DIR}")
    if settings.RAILWAY_VOLUME_MOUNT_PATH:
        logger.info(f"Используется Railway Volume: {settings.RAILWAY_VOLUME_NAME}")
        logger.info(f"Путь монтирования: {settings.RAILWAY_VOLUME_MOUNT_PATH}")

async def wait_for_request_limit(user_id: int):
    """
    Ожидает, если необходимо, чтобы соблюсти ограничения на частоту запросов
    
    Args:
        user_id: ID пользователя
    """
    current_time = time.time()
    if user_id in last_request_time:
        elapsed = current_time - last_request_time[user_id]
        if elapsed < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - elapsed
            logger.info(f"Ожидаем {wait_time:.2f} секунд перед следующим запросом для пользователя {user_id}")
            await asyncio.sleep(wait_time)
    
    last_request_time[user_id] = time.time()

async def get_client(user_id: int) -> TelegramClient:
    """
    Получает или создает клиент Telegram для пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        TelegramClient: Клиент Telegram
    """
    logger.info(f"Запрос на получение клиента для пользователя {user_id}")
    
    # Соблюдаем ограничения на частоту запросов
    await wait_for_request_limit(user_id)
    
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
    
    # Проверяем существование директории сессий
    if not os.path.exists(settings.SESSIONS_DIR):
        try:
            os.makedirs(settings.SESSIONS_DIR, exist_ok=True)
            logger.info(f"Создана директория сессий: {settings.SESSIONS_DIR}")
        except Exception as e:
            logger.error(f"Ошибка при создании директории сессий: {str(e)}")
            raise ValueError(f"Не удалось создать директорию сессий: {str(e)}")
    
    # Создаем путь к файлу сессии
    session_file = os.path.join(settings.SESSIONS_DIR, f"user_{user_id}")
    logger.info(f"Путь к файлу сессии: {session_file}")
    logger.info(f"Полный путь к директории сессий: {os.path.abspath(settings.SESSIONS_DIR)}")
    
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
            # Проверяем права на запись в директорию сессий
            try:
                test_file = os.path.join(settings.SESSIONS_DIR, "test_write_permission.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                logger.info(f"Проверка прав на запись в директорию сессий успешна")
            except Exception as e:
                logger.error(f"Нет прав на запись в директорию сессий: {str(e)}")
                raise ValueError(f"Нет прав на запись в директорию сессий: {str(e)}")
            
            # Создаем пустой файл сессии для тестирования
            try:
                with open(f"{session_file}.session", 'w') as f:
                    f.write("")
                logger.info(f"Создан пустой файл сессии для тестирования: {session_file}.session")
                
                # Если удалось создать файл, значит, права на запись есть, но сессия отсутствует
                os.remove(f"{session_file}.session")
                logger.info(f"Пустой файл сессии удален: {session_file}.session")
                
                raise ValueError(f"Сессия для пользователя {user_id} не найдена. Необходима авторизация.")
            except Exception as e:
                logger.error(f"Ошибка при создании пустого файла сессии: {str(e)}")
                raise ValueError(f"Нет прав на запись файла сессии: {str(e)}")
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
        settings.TELEGRAM_API_HASH,
        device_model="Telegram Dialogs Viewer Web"
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
            
            # Проверяем, существует ли файл сессии
            if os.path.exists(f"{session_file}.session"):
                # Если файл существует, но авторизация не работает, пробуем удалить его
                try:
                    os.remove(f"{session_file}.session")
                    logger.info(f"Удален некорректный файл сессии: {session_file}.session")
                except Exception as e:
                    logger.error(f"Ошибка при удалении некорректного файла сессии: {str(e)}")
            
            raise ValueError("Пользователь не авторизован. Требуется повторная авторизация.")
        
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
        
        # Соблюдаем ограничения на частоту запросов
        await wait_for_request_limit(temp_user_id)
        
        # Создаем путь к файлу сессии
        session_file = os.path.join(settings.SESSIONS_DIR, f"temp_user_{temp_user_id}")
        logger.info(f"Путь к временному файлу сессии: {session_file}")
        logger.info(f"Директория сессий существует: {os.path.exists(settings.SESSIONS_DIR)}")
        
        # Создаем клиент
        client = TelegramClient(
            session_file,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
            device_model="Telegram Dialogs Viewer Web"
        )
        
        # Подключаемся к Telegram
        await client.connect()
        
        # Отправляем запрос на получение кода
        try:
            sent_code = await client.send_code_request(phone_number)
        except FloodWaitError as e:
            # Если превышен лимит запросов, сообщаем пользователю, сколько нужно подождать
            logger.error(f"Превышен лимит запросов к API Telegram: {str(e)}")
            raise ValueError(f"Превышен лимит запросов к API Telegram. Пожалуйста, подождите {e.seconds} секунд и попробуйте снова.")
        except UserDeactivatedBanError:
            logger.error(f"Аккаунт заблокирован Telegram")
            raise ValueError("Ваш аккаунт Telegram заблокирован. Пожалуйста, обратитесь в поддержку Telegram.")
        except Exception as e:
            logger.error(f"Ошибка при отправке кода: {str(e)}")
            raise ValueError(f"Ошибка при отправке кода: {str(e)}")
        
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
        
        # Соблюдаем ограничения на частоту запросов
        await wait_for_request_limit(temp_user_id)
        
        try:
            # Пытаемся авторизоваться по коду
            logger.info(f"Авторизация по коду для номера {phone_number}")
            user = await client.sign_in(
                phone=phone_number,
                code=code,
                phone_code_hash=phone_code_hash
            )
            logger.info(f"Успешная авторизация по коду для номера {phone_number}")
        except FloodWaitError as e:
            # Если превышен лимит запросов, сообщаем пользователю, сколько нужно подождать
            logger.error(f"Превышен лимит запросов к API Telegram: {str(e)}")
            raise ValueError(f"Превышен лимит запросов к API Telegram. Пожалуйста, подождите {e.seconds} секунд и попробуйте снова.")
        except UserDeactivatedBanError:
            logger.error(f"Аккаунт заблокирован Telegram")
            raise ValueError("Ваш аккаунт Telegram заблокирован. Пожалуйста, обратитесь в поддержку Telegram.")
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
        
        # Проверяем существование директории сессий
        if not os.path.exists(settings.SESSIONS_DIR):
            try:
                os.makedirs(settings.SESSIONS_DIR, exist_ok=True)
                logger.info(f"Создана директория сессий: {settings.SESSIONS_DIR}")
            except Exception as e:
                logger.error(f"Ошибка при создании директории сессий: {str(e)}")
                raise ValueError(f"Не удалось создать директорию сессий: {str(e)}")
        
        # Явно сохраняем сессию
        try:
            # Проверяем, что сессия существует и имеет метод save
            if client.session and hasattr(client.session, 'save'):
                if asyncio.iscoroutinefunction(client.session.save):
                    await client.session.save()
                else:
                    client.session.save()
                logger.info(f"Сессия сохранена явно")
            else:
                logger.warning(f"Не удалось сохранить сессию: объект сессии отсутствует или не имеет метода save")
        except Exception as e:
            logger.error(f"Ошибка при явном сохранении сессии: {str(e)}")
            raise ValueError(f"Не удалось сохранить сессию: {str(e)}")
        
        # Перемещаем сессию из временной в постоянную
        temp_session_file = os.path.join(settings.SESSIONS_DIR, f"temp_user_{temp_user_id}")
        permanent_session_file = os.path.join(settings.SESSIONS_DIR, f"user_{me.id}")
        logger.info(f"Перемещаем сессию из {temp_session_file} в {permanent_session_file}")
        
        if os.path.exists(f"{temp_session_file}.session"):
            try:
                # Проверяем права на запись в директорию сессий
                try:
                    test_file = os.path.join(settings.SESSIONS_DIR, "test_write_permission.tmp")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    logger.info(f"Проверка прав на запись в директорию сессий успешна")
                except Exception as e:
                    logger.error(f"Нет прав на запись в директорию сессий: {str(e)}")
                    raise ValueError(f"Нет прав на запись в директорию сессий: {str(e)}")
                
                # Копируем файл сессии
                import shutil
                try:
                    shutil.copy(f"{temp_session_file}.session", f"{permanent_session_file}.session")
                    logger.info(f"Сессия успешно скопирована")
                    
                    # Проверяем, что файл был скопирован
                    if os.path.exists(f"{permanent_session_file}.session"):
                        logger.info(f"Файл сессии успешно создан: {permanent_session_file}.session")
                        
                        # Проверяем размер файла сессии
                        file_size = os.path.getsize(f"{permanent_session_file}.session")
                        logger.info(f"Размер файла сессии: {file_size} байт")
                        
                        if file_size == 0:
                            logger.error(f"Файл сессии пуст: {permanent_session_file}.session")
                            raise ValueError(f"Файл сессии пуст: {permanent_session_file}.session")
                        
                        # Удаляем временный файл сессии
                        try:
                            os.remove(f"{temp_session_file}.session")
                            logger.info(f"Временный файл сессии удален")
                        except Exception as e:
                            logger.error(f"Ошибка при удалении временного файла сессии: {str(e)}")
                    else:
                        logger.error(f"Файл сессии не был создан: {permanent_session_file}.session")
                        raise ValueError(f"Файл сессии не был создан: {permanent_session_file}.session")
                except Exception as copy_error:
                    logger.error(f"Ошибка при копировании сессии: {str(copy_error)}")
                    raise ValueError(f"Ошибка при копировании сессии: {str(copy_error)}")
            except Exception as e:
                logger.error(f"Ошибка при работе с файлами сессий: {str(e)}")
                raise ValueError(f"Ошибка при работе с файлами сессий: {str(e)}")
        else:
            logger.warning(f"Файл сессии не найден: {temp_session_file}.session")
            
            # Проверяем содержимое директории сессий
            try:
                session_files = os.listdir(settings.SESSIONS_DIR)
                logger.info(f"Файлы в директории сессий: {session_files}")
            except Exception as e:
                logger.error(f"Ошибка при чтении директории сессий: {str(e)}")
            
            raise ValueError(f"Файл сессии не найден: {temp_session_file}.session")
        
        # Создаем новый клиент с постоянным файлом сессии
        try:
            new_client = TelegramClient(
                permanent_session_file,
                settings.TELEGRAM_API_ID,
                settings.TELEGRAM_API_HASH,
                device_model="Telegram Dialogs Viewer Web"
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


async def sign_in_2fa(
    temp_user_id: int,
    phone_number: str,
    code: str,
    phone_code_hash: str,
    password: str
) -> Dict[str, Any]:
    """
    Авторизация по коду подтверждения с двухфакторной аутентификацией
    
    Args:
        temp_user_id: Временный ID пользователя
        phone_number: Номер телефона
        code: Код подтверждения
        phone_code_hash: Хеш кода подтверждения
        password: Пароль для двухфакторной аутентификации
    
    Returns:
        Dict[str, Any]: Данные пользователя
    """
    logger.info(f"Авторизация с 2FA для номера {phone_number}")
    
    # Используем существующую функцию sign_in с паролем
    return await sign_in(
        temp_user_id=temp_user_id,
        phone_number=phone_number,
        code=code,
        phone_code_hash=phone_code_hash,
        password=password
    )


async def get_dialogs(user_id: int, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Получает список диалогов пользователя
    """
    # Проверяем кэш, если не требуется принудительное обновление
    if not force_refresh and user_id in dialogs_cache:
        cached_dialogs, timestamp = dialogs_cache[user_id]
        # Если кэш не устарел, возвращаем его
        if time.time() - timestamp < CACHE_TTL:
            logger.info(f"Возвращаем кэшированные диалоги для пользователя {user_id}")
            return cached_dialogs
        else:
            logger.info(f"Кэш диалогов для пользователя {user_id} устарел")

    try:
        # Получаем клиент Telegram
        client = await get_client(user_id)
        
        # Ждем ограничения запросов
        await wait_for_request_limit(user_id)
        
        # Получаем диалоги
        logger.info(f"Получаем диалоги для пользователя {user_id}")
        dialogs = await client.get_dialogs()
        
        # Преобразуем диалоги в список словарей
        result = []
        for dialog in dialogs:
            dialog_dict = {
                "id": dialog.id,
                "title": dialog.title or dialog.name or "Без названия",
                "type": str(dialog.entity_type) if hasattr(dialog, 'entity_type') else "unknown",
                "unread_count": dialog.unread_count if hasattr(dialog, 'unread_count') else 0,
            }
            
            # Добавляем последнее сообщение, если оно есть
            if hasattr(dialog, 'message') and dialog.message:
                dialog_dict["last_message"] = dialog.message.message if hasattr(dialog.message, 'message') else ""
                dialog_dict["last_message_date"] = dialog.message.date.isoformat() if hasattr(dialog.message, 'date') else ""
            
            # Добавляем фото профиля, если оно есть
            try:
                if hasattr(dialog, 'entity') and dialog.entity:
                    # Получаем аватар диалога
                    photo_url = await get_dialog_photo(client, dialog)
                    if photo_url:
                        dialog_dict["photo"] = photo_url
            except Exception as e:
                logger.warning(f"Ошибка при получении фото для диалога {dialog.id}: {e}")
            
            result.append(dialog_dict)
        
        # Сохраняем результат в кэш
        dialogs_cache[user_id] = (result, time.time())
        
        logger.info(f"Получено {len(result)} диалогов для пользователя {user_id}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов для пользователя {user_id}: {e}")
        
        # Собираем подробную информацию об ошибке
        session_file = os.path.join(settings.SESSIONS_DIR, f"user_{user_id}.session")
        session_exists = os.path.exists(session_file)
        sessions_list = os.listdir(settings.SESSIONS_DIR) if os.path.exists(settings.SESSIONS_DIR) else []
        
        error_message = f"Ошибка при получении диалогов: {str(e)}. "
        error_message += f"Пользователь: {user_id}. "
        error_message += f"Время: {datetime.now().isoformat()}. "
        error_message += f"Сессия: {session_file}. "
        error_message += f"Сессия существует: {session_exists}. "
        error_message += f"Содержимое директории сессий: {', '.join(sessions_list)}."
        
        # Проверяем тип ошибки
        if "FloodWaitError" in str(e):
            raise ValueError(f"Превышен лимит запросов к API Telegram: {str(e)}")
        elif "UserDeactivatedBanError" in str(e) or "UserBannedInChannelError" in str(e):
            raise ValueError(f"Аккаунт заблокирован Telegram: {str(e)}")
        elif "AuthKeyUnregisteredError" in str(e) or "AuthKeyError" in str(e):
            raise ValueError(f"Сессия для пользователя {user_id} не найдена или недействительна: {str(e)}")
        elif "SessionPasswordNeededError" in str(e):
            raise ValueError(f"Требуется пароль двухфакторной аутентификации: {str(e)}")
        else:
            # Выбрасываем исключение с подробной информацией
            raise ValueError(error_message)


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


async def get_messages(user_id: int, dialog_id: str, limit: int = 50, offset: int = 0, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Получает сообщения из диалога
    
    Args:
        user_id: ID пользователя
        dialog_id: ID диалога
        limit: Максимальное количество сообщений
        offset: Смещение (для пагинации)
        force_refresh: Принудительное обновление кэша
        
    Returns:
        List[Dict[str, Any]]: Список сообщений
    """
    # Создаем ключ для кэша
    cache_key = (user_id, dialog_id, limit, offset)
    
    # Проверяем кэш, если не требуется принудительное обновление
    if not force_refresh and cache_key in messages_cache:
        cached_messages, timestamp = messages_cache[cache_key]
        # Если кэш не устарел, возвращаем его
        if time.time() - timestamp < CACHE_TTL:
            logger.info(f"Возвращаем кэшированные сообщения для пользователя {user_id} и диалога {dialog_id}")
            return cached_messages
        else:
            logger.info(f"Кэш сообщений для пользователя {user_id} и диалога {dialog_id} устарел")
    
    try:
        # Получаем клиент Telegram
        client = await get_client(user_id)
        
        # Ждем ограничения запросов
        await wait_for_request_limit(user_id)
        
        # Получаем сущность диалога
        logger.info(f"Получаем сущность диалога {dialog_id} для пользователя {user_id}")
        entity = await client.get_entity(int(dialog_id))
        
        # Получаем сообщения
        logger.info(f"Получаем сообщения для диалога {dialog_id} (лимит: {limit}, смещение: {offset})")
        messages = await client.get_messages(entity, limit=limit, offset_id=offset)
        
        # Преобразуем сообщения в список словарей
        result = []
        for message in messages:
            # Базовая информация о сообщении
            message_dict = {
                "id": message.id,
                "text": message.text if hasattr(message, 'text') else "",
                "date": message.date.isoformat() if hasattr(message, 'date') else None,
                "out": message.out if hasattr(message, 'out') else False,
                "mentioned": message.mentioned if hasattr(message, 'mentioned') else False,
                "media_unread": message.media_unread if hasattr(message, 'media_unread') else False,
                "silent": message.silent if hasattr(message, 'silent') else False,
                "post": message.post if hasattr(message, 'post') else False,
                "from_scheduled": message.from_scheduled if hasattr(message, 'from_scheduled') else False,
                "legacy": message.legacy if hasattr(message, 'legacy') else False,
                "edit_hide": message.edit_hide if hasattr(message, 'edit_hide') else False,
                "pinned": message.pinned if hasattr(message, 'pinned') else False,
                "noforwards": message.noforwards if hasattr(message, 'noforwards') else False,
            }
            
            # Информация об отправителе
            if hasattr(message, 'sender') and message.sender:
                sender = message.sender
                sender_dict = {
                    "id": sender.id if hasattr(sender, 'id') else None,
                    "first_name": sender.first_name if hasattr(sender, 'first_name') else None,
                    "last_name": sender.last_name if hasattr(sender, 'last_name') else None,
                    "username": sender.username if hasattr(sender, 'username') else None,
                    "phone": sender.phone if hasattr(sender, 'phone') else None,
                    "bot": sender.bot if hasattr(sender, 'bot') else False,
                }
                
                # Получаем аватар отправителя
                try:
                    sender_dict["photo"] = await get_profile_photo(client, sender)
                except Exception as e:
                    logger.warning(f"Ошибка при получении аватара отправителя: {e}")
                
                message_dict["sender"] = sender_dict
            
            # Информация о медиа
            if hasattr(message, 'media') and message.media:
                media = message.media
                media_dict = {
                    "type": str(type(media).__name__),
                }
                
                # Обрабатываем разные типы медиа
                if hasattr(media, 'photo') and media.photo:
                    media_dict["photo"] = True
                    # Можно добавить логику для получения URL фото
                
                if hasattr(media, 'document') and media.document:
                    media_dict["document"] = True
                    # Можно добавить логику для получения информации о документе
                
                message_dict["media"] = media_dict
            
            # Информация о пересланном сообщении
            if hasattr(message, 'forward') and message.forward:
                forward = message.forward
                forward_dict = {
                    "date": forward.date.isoformat() if hasattr(forward, 'date') else None,
                }
                
                if hasattr(forward, 'from_id') and forward.from_id:
                    forward_dict["from_id"] = str(forward.from_id)
                
                if hasattr(forward, 'from_name') and forward.from_name:
                    forward_dict["from_name"] = forward.from_name
                
                message_dict["forward"] = forward_dict
            
            # Информация о реакциях
            if hasattr(message, 'reactions') and message.reactions:
                reactions = message.reactions
                reactions_list = []
                
                if hasattr(reactions, 'results') and reactions.results:
                    for reaction in reactions.results:
                        reaction_dict = {
                            "emoticon": reaction.emoticon if hasattr(reaction, 'emoticon') else None,
                            "count": reaction.count if hasattr(reaction, 'count') else 0,
                        }
                        reactions_list.append(reaction_dict)
                
                message_dict["reactions"] = reactions_list
            
            result.append(message_dict)
        
        # Сохраняем результат в кэш
        messages_cache[cache_key] = (result, time.time())
        
        logger.info(f"Получено {len(result)} сообщений для диалога {dialog_id}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений для диалога {dialog_id}: {e}")
        
        # Проверяем тип ошибки
        if "FloodWaitError" in str(e):
            raise ValueError(f"Превышен лимит запросов к API Telegram: {str(e)}")
        elif "UserDeactivatedBanError" in str(e) or "UserBannedInChannelError" in str(e):
            raise ValueError(f"Аккаунт заблокирован Telegram: {str(e)}")
        elif "AuthKeyUnregisteredError" in str(e) or "AuthKeyError" in str(e):
            raise ValueError(f"Сессия для пользователя {user_id} не найдена или недействительна: {str(e)}")
        elif "SessionPasswordNeededError" in str(e):
            raise ValueError(f"Требуется пароль двухфакторной аутентификации: {str(e)}")
        else:
            # Выбрасываем исключение с подробной информацией
            raise ValueError(f"Ошибка при получении сообщений: {str(e)}")


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
        
        # Соблюдаем ограничения на частоту запросов
        await wait_for_request_limit(user_id)
        
        # Отправляем сообщение
        try:
            message = await client.send_message(
                dialog_id,
                text,
                reply_to=reply_to
            )
        except FloodWaitError as e:
            # Если превышен лимит запросов, сообщаем пользователю, сколько нужно подождать
            logger.error(f"Превышен лимит запросов к API Telegram: {str(e)}")
            raise ValueError(f"Превышен лимит запросов к API Telegram. Пожалуйста, подождите {e.seconds} секунд и попробуйте снова.")
        except UserDeactivatedBanError:
            logger.error(f"Аккаунт заблокирован Telegram")
            raise ValueError("Ваш аккаунт Telegram заблокирован. Пожалуйста, обратитесь в поддержку Telegram.")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {str(e)}")
            raise ValueError(f"Ошибка при отправке сообщения: {str(e)}")
        
        # Форматируем результат
        result = {
            "id": message.id,
            "text": message.message,
            "date": message.date.isoformat(),
            "out": message.out
        }
        
        # Инвалидируем кэш сообщений для этого диалога
        cache_key = (user_id, dialog_id)
        if cache_key in messages_cache:
            del messages_cache[cache_key]
            logger.info(f"Кэш сообщений для диалога {dialog_id} инвалидирован после отправки сообщения")
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {str(e)}")
        raise


async def get_session_info(user_id: int) -> Dict[str, Any]:
    """
    Получает информацию о сессии пользователя для отладки
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Dict[str, Any]: Информация о сессии
    """
    logger.info(f"Получение информации о сессии для пользователя {user_id}")
    
    # Создаем путь к файлу сессии
    session_file = os.path.join(settings.SESSIONS_DIR, f"user_{user_id}")
    session_file_path = f"{session_file}.session"
    
    # Проверяем существование директории сессий
    sessions_dir_exists = os.path.exists(settings.SESSIONS_DIR)
    
    # Проверяем существование файла сессии
    session_exists = os.path.exists(session_file_path)
    
    # Получаем список файлов сессий
    sessions_list = []
    if sessions_dir_exists:
        try:
            all_files = os.listdir(settings.SESSIONS_DIR)
            sessions_list = [f for f in all_files if f.endswith('.session')]
        except Exception as e:
            logger.error(f"Ошибка при получении списка файлов сессий: {str(e)}")
    
    # Проверяем права на запись
    write_permission = False
    if sessions_dir_exists:
        try:
            test_file = os.path.join(settings.SESSIONS_DIR, "test_write_permission.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            write_permission = True
        except Exception as e:
            logger.error(f"Нет прав на запись в директорию сессий: {str(e)}")
    
    # Получаем размер файла сессии
    session_size = 0
    if session_exists:
        try:
            session_size = os.path.getsize(session_file_path)
        except Exception as e:
            logger.error(f"Ошибка при получении размера файла сессии: {str(e)}")
    
    # Формируем информацию о сессии
    session_info = {
        "user_id": user_id,
        "session_path": session_file_path,
        "sessions_dir": settings.SESSIONS_DIR,
        "sessions_dir_exists": sessions_dir_exists,
        "session_exists": session_exists,
        "session_size": session_size,
        "write_permission": write_permission,
        "sessions_list": sessions_list,
        "is_railway": settings.IS_RAILWAY,
        "railway_volume": settings.RAILWAY_VOLUME_NAME if settings.IS_RAILWAY else None,
        "railway_volume_path": settings.RAILWAY_VOLUME_MOUNT_PATH if settings.IS_RAILWAY else None
    }
    
    logger.info(f"Информация о сессии: {session_info}")
    return session_info


async def get_profile_photo(client, entity) -> Optional[str]:
    """
    Получает URL аватара профиля
    
    Args:
        client: Клиент Telegram
        entity: Сущность (пользователь, чат, канал)
        
    Returns:
        Optional[str]: URL аватара или None, если аватар отсутствует
    """
    try:
        # Проверяем, есть ли у сущности фото профиля
        if not hasattr(entity, 'photo') or not entity.photo:
            return None
        
        # Получаем фото профиля
        photos = await client.get_profile_photos(entity)
        if not photos or len(photos) == 0:
            return None
        
        # Берем первое (самое новое) фото
        photo = photos[0]
        
        # Получаем размер фото (предпочитаем маленький размер для аватаров)
        smallest_size = None
        for size in photo.sizes:
            if smallest_size is None or (hasattr(size, 'size') and size.size < smallest_size.size):
                smallest_size = size
        
        if not smallest_size:
            return None
        
        # Скачиваем фото
        photo_data = await client.download_media(photo, bytes)
        
        # Кодируем фото в base64 для отображения в браузере
        import base64
        photo_base64 = base64.b64encode(photo_data).decode('utf-8')
        
        # Определяем MIME-тип (обычно image/jpeg для фото профиля)
        mime_type = "image/jpeg"
        
        # Формируем data URL
        data_url = f"data:{mime_type};base64,{photo_base64}"
        
        return data_url
    except Exception as e:
        logger.warning(f"Ошибка при получении аватара: {e}")
        return None


async def get_dialog_photo(client, dialog) -> Optional[str]:
    """
    Получает URL аватара диалога
    
    Args:
        client: Клиент Telegram
        dialog: Диалог
        
    Returns:
        Optional[str]: URL аватара или None, если аватар отсутствует
    """
    try:
        # Проверяем, есть ли у диалога сущность
        if not hasattr(dialog, 'entity') or not dialog.entity:
            return None
        
        # Получаем аватар сущности
        return await get_profile_photo(client, dialog.entity)
    except Exception as e:
        logger.warning(f"Ошибка при получении аватара диалога: {e}")
        return None 