"""
API для работы с диалогами Telegram
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from pydantic import BaseModel
import random
from datetime import datetime, timedelta
import os

from app.core.security import verify_token, TokenData
from app.services.telegram import get_dialogs, get_messages, send_message

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем роутер
router = APIRouter()

# Модель диалога
class Dialog(BaseModel):
    id: str
    title: str
    last_message: Optional[str] = None
    last_message_date: Optional[str] = None
    unread_count: int = 0
    photo: Optional[str] = None

# Функция для получения текущего пользователя из токена
def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Получает текущего пользователя из токена авторизации
    """
    if not authorization:
        logger.error("Не указан токен авторизации")
        raise HTTPException(status_code=401, detail="Не указан токен авторизации")
    
    try:
        # Проверяем формат токена
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            logger.error(f"Неверный формат токена: {scheme}")
            raise HTTPException(status_code=401, detail="Неверный формат токена")
        
        logger.info(f"Проверяем токен: {token[:10]}...")
        
        # Проверяем токен
        token_data = verify_token(token)
        if not token_data:
            logger.error("Токен не прошел проверку")
            raise HTTPException(status_code=401, detail="Неверный токен авторизации")
        
        logger.info(f"Токен прошел проверку, user_id: {token_data.user_id}")
        
        return {"id": token_data.user_id}
    except Exception as e:
        logger.error(f"Ошибка при проверке токена: {e}")
        raise HTTPException(status_code=401, detail="Неверный токен авторизации")

# Эндпоинт для получения списка диалогов
@router.get("/", response_model=List[Dict[str, Any]])
async def list_dialogs(
    force_refresh: bool = Query(False, description="Принудительно обновить кэш"),
    current_user = Depends(get_current_user)
):
    """
    Получает список диалогов пользователя
    """
    try:
        user_id = current_user['id']
        logger.info(f"Получение диалогов для пользователя {user_id}, force_refresh={force_refresh}")
        
        # Преобразуем ID пользователя в целое число
        try:
            user_id_int = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать ID пользователя '{user_id}' в целое число")
            raise HTTPException(status_code=400, detail="Неверный формат ID пользователя")
        
        # Получаем диалоги из Telegram
        try:
            dialogs = await get_dialogs(user_id_int, force_refresh=force_refresh)
            logger.info(f"Получено {len(dialogs)} диалогов для пользователя {user_id}")
            return dialogs
        except ValueError as e:
            logger.error(f"Ошибка при получении диалогов: {e}")
            error_message = str(e)
            
            if "Превышен лимит запросов к API Telegram" in error_message:
                # Если превышен лимит запросов, возвращаем соответствующую ошибку
                raise HTTPException(status_code=429, detail=error_message)
            elif "Аккаунт заблокирован Telegram" in error_message:
                # Если аккаунт заблокирован, возвращаем соответствующую ошибку
                raise HTTPException(status_code=403, detail=error_message)
            elif "Сессия для пользователя" in error_message and "не найдена" in error_message:
                # Добавляем подробную информацию о сессии
                session_path = f"/app/backend/app/sessions/user_{user_id_int}.session"
                session_exists = os.path.exists(session_path)
                sessions_dir = "/app/backend/app/sessions"
                sessions_dir_exists = os.path.exists(sessions_dir)
                sessions_list = os.listdir(sessions_dir) if sessions_dir_exists else []
                
                detail = {
                    "message": "Требуется авторизация в Telegram",
                    "error": error_message,
                    "session_info": {
                        "user_id": user_id_int,
                        "session_path": session_path,
                        "session_exists": session_exists,
                        "sessions_dir_exists": sessions_dir_exists,
                        "sessions_list": sessions_list
                    }
                }
                raise HTTPException(status_code=401, detail=detail)
            elif "Пользователь не авторизован" in error_message:
                raise HTTPException(status_code=401, detail="Требуется авторизация в Telegram")
            else:
                # Возвращаем подробную информацию об ошибке
                raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {e}")
        # Возвращаем подробную информацию об ошибке
        error_detail = {
            "message": "Внутренняя ошибка сервера",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        raise HTTPException(status_code=500, detail=error_detail)

# Эндпоинт для получения сообщений из диалога
@router.get("/{dialog_id}/messages", response_model=List[Dict[str, Any]])
async def list_messages(
    dialog_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset_id: int = Query(0, ge=0),
    force_refresh: bool = Query(False, description="Принудительно обновить кэш"),
    current_user = Depends(get_current_user)
):
    """
    Получает сообщения из диалога
    """
    try:
        user_id = current_user['id']
        logger.info(f"Получение сообщений из диалога {dialog_id} для пользователя {user_id}, limit={limit}, offset_id={offset_id}, force_refresh={force_refresh}")
        
        # Преобразуем ID пользователя в целое число
        try:
            user_id_int = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать ID пользователя '{user_id}' в целое число")
            raise HTTPException(status_code=400, detail="Неверный формат ID пользователя")
        
        # Получаем сообщения из Telegram
        try:
            messages = await get_messages(user_id_int, dialog_id, limit, offset_id, force_refresh=force_refresh)
            logger.info(f"Получено {len(messages)} сообщений из диалога {dialog_id}")
            return messages
        except ValueError as e:
            logger.error(f"Ошибка при получении сообщений: {e}")
            error_message = str(e)
            
            if "Превышен лимит запросов к API Telegram" in error_message:
                # Если превышен лимит запросов, возвращаем соответствующую ошибку
                raise HTTPException(status_code=429, detail=error_message)
            elif "Аккаунт заблокирован Telegram" in error_message:
                # Если аккаунт заблокирован, возвращаем соответствующую ошибку
                raise HTTPException(status_code=403, detail=error_message)
            elif "Сессия для пользователя" in error_message and "не найдена" in error_message:
                # Добавляем подробную информацию о сессии
                session_path = f"/app/backend/app/sessions/user_{user_id_int}.session"
                session_exists = os.path.exists(session_path)
                sessions_dir = "/app/backend/app/sessions"
                sessions_dir_exists = os.path.exists(sessions_dir)
                sessions_list = os.listdir(sessions_dir) if sessions_dir_exists else []
                
                detail = {
                    "message": "Требуется авторизация в Telegram",
                    "error": error_message,
                    "session_info": {
                        "user_id": user_id_int,
                        "session_path": session_path,
                        "session_exists": session_exists,
                        "sessions_dir_exists": sessions_dir_exists,
                        "sessions_list": sessions_list
                    }
                }
                raise HTTPException(status_code=401, detail=detail)
            else:
                # Возвращаем подробную информацию об ошибке
                raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений: {e}")
        # Возвращаем подробную информацию об ошибке
        error_detail = {
            "message": "Внутренняя ошибка сервера",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        raise HTTPException(status_code=500, detail=error_detail)

# Эндпоинт для отправки сообщения в диалог
@router.post("/{dialog_id}/messages", response_model=Dict[str, Any])
async def send_dialog_message(
    dialog_id: int,
    message: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """
    Отправляет сообщение в диалог
    """
    try:
        user_id = current_user['id']
        logger.info(f"Отправка сообщения в диалог {dialog_id} от пользователя {user_id}")
        
        # Проверяем, что сообщение содержит текст
        if "text" not in message or not message["text"]:
            raise HTTPException(status_code=400, detail="Сообщение должно содержать текст")
        
        # Преобразуем ID пользователя в целое число
        try:
            user_id_int = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать ID пользователя '{user_id}' в целое число")
            raise HTTPException(status_code=400, detail="Неверный формат ID пользователя")
        
        # Отправляем сообщение
        try:
            reply_to = message.get("reply_to")
            result = await send_message(user_id_int, dialog_id, message["text"], reply_to)
            logger.info(f"Сообщение успешно отправлено в диалог {dialog_id}")
            return result
        except ValueError as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            error_message = str(e)
            
            if "Превышен лимит запросов к API Telegram" in error_message:
                # Если превышен лимит запросов, возвращаем соответствующую ошибку
                raise HTTPException(status_code=429, detail=error_message)
            elif "Аккаунт заблокирован Telegram" in error_message:
                # Если аккаунт заблокирован, возвращаем соответствующую ошибку
                raise HTTPException(status_code=403, detail=error_message)
            else:
                raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Эндпоинт для получения конкретного диалога
@router.get("/{dialog_id}", response_model=Dialog)
async def get_dialog(dialog_id: str, current_user = Depends(get_current_user)):
    """
    Получает информацию о конкретном диалоге
    """
    logger.info(f"Получение диалога {dialog_id} для пользователя {current_user['id']}")
    
    # В реальном приложении здесь должен быть запрос к API Telegram
    # В данном случае возвращаем тестовые данные
    now = datetime.now()
    
    dialog = Dialog(
        id=dialog_id,
        title=f"Диалог {dialog_id}",
        last_message="Тестовое сообщение",
        last_message_date=now.isoformat(),
        unread_count=0
    )
    
    return dialog 