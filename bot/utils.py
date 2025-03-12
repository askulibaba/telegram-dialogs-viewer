import os
import logging
from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel

logger = logging.getLogger(__name__)

async def init_telegram_client(user_id: str, api_id: str, api_hash: str) -> TelegramClient:
    """Инициализация клиента Telegram."""
    try:
        session_file = os.path.join('sessions', f'{user_id}.session')
        client = TelegramClient(session_file, api_id, api_hash)
        
        if not client.is_connected():
            await client.connect()
            logger.info(f"Клиент для пользователя {user_id} подключен")
            
        if not await client.is_user_authorized():
            logger.error(f"Пользователь {user_id} не авторизован в Telethon")
            raise Exception("Требуется авторизация в Telegram")
            
        return client
    except Exception as e:
        logger.error(f"Ошибка при инициализации клиента: {str(e)}")
        raise

async def get_dialogs(client: TelegramClient, limit: int = 20):
    """Получение списка диалогов пользователя."""
    try:
        dialogs = await client.get_dialogs(limit=limit)
        
        result = []
        for dialog in dialogs:
            try:
                entity = dialog.entity
                
                dialog_info = {
                    'id': entity.id,
                    'name': '',
                    'type': '',
                    'unread_count': dialog.unread_count,
                    'last_message': dialog.message.message if dialog.message else None,
                    'last_message_date': str(dialog.message.date) if dialog.message else None
                }
                
                if isinstance(entity, User):
                    dialog_info['name'] = f"{entity.first_name} {entity.last_name if entity.last_name else ''}"
                    dialog_info['type'] = 'user'
                elif isinstance(entity, Chat):
                    dialog_info['name'] = entity.title
                    dialog_info['type'] = 'chat'
                elif isinstance(entity, Channel):
                    dialog_info['name'] = entity.title
                    dialog_info['type'] = 'channel'
                    
                result.append(dialog_info)
            except Exception as e:
                logger.error(f"Ошибка при обработке диалога: {str(e)}")
                continue
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {str(e)}")
        raise

def verify_telegram_auth(token: str, auth_data: dict) -> bool:
    """Проверка данных аутентификации от Telegram Login Widget."""
    import hmac
    import hashlib
    import time
    
    try:
        if 'hash' not in auth_data:
            logger.error("Отсутствует hash в данных авторизации")
            return False
            
        auth_data = auth_data.copy()
        auth_hash = auth_data.pop('hash')
        
        # Проверяем срок действия авторизации (24 часа)
        auth_date = int(auth_data.get('auth_date', 0))
        if time.time() - auth_date > 86400:
            logger.error("Срок действия авторизации истек")
            return False
            
        # Формируем строку для проверки
        data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(auth_data.items())])
        secret_key = hashlib.sha256(token.encode()).digest()
        
        # Вычисляем и сравниваем хеш
        hash_str = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hash_str == auth_hash
    except Exception as e:
        logger.error(f"Ошибка при проверке данных авторизации: {str(e)}")
        return False 