"""
API для работы с диалогами Telegram
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from pydantic import BaseModel
import random
from datetime import datetime, timedelta

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
async def list_dialogs(current_user = Depends(get_current_user)):
    """
    Получает список диалогов пользователя
    """
    try:
        user_id = current_user['id']
        logger.info(f"Получение диалогов для пользователя {user_id}")
        
        # Преобразуем ID пользователя в целое число
        try:
            user_id_int = int(user_id)
        except ValueError:
            logger.error(f"Невозможно преобразовать ID пользователя '{user_id}' в целое число")
            raise HTTPException(status_code=400, detail="Неверный формат ID пользователя")
        
        # Получаем диалоги из Telegram
        try:
            dialogs = await get_dialogs(user_id_int)
            logger.info(f"Получено {len(dialogs)} диалогов для пользователя {user_id}")
            return dialogs
        except ValueError as e:
            logger.error(f"Ошибка при получении диалогов: {e}")
            if "Сессия для пользователя" in str(e) and "не найдена" in str(e):
                raise HTTPException(status_code=401, detail="Требуется авторизация в Telegram")
            elif "Пользователь не авторизован" in str(e):
                raise HTTPException(status_code=401, detail="Требуется авторизация в Telegram")
            else:
                raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Эндпоинт для получения сообщений из диалога
@router.get("/{dialog_id}/messages", response_model=List[Dict[str, Any]])
async def list_messages(
    dialog_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset_id: int = Query(0, ge=0),
    current_user = Depends(get_current_user)
):
    """
    Получает сообщения из диалога
    """
    try:
        logger.info(f"Получение сообщений из диалога {dialog_id} для пользователя {current_user['id']}")
        
        # Получаем сообщения из Telegram
        messages = await get_messages(
            int(current_user['id']),
            dialog_id,
            limit=limit,
            offset_id=offset_id
        )
        
        return messages
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        logger.info(f"Отправка сообщения в диалог {dialog_id} от пользователя {current_user['id']}")
        
        # Проверяем, что сообщение содержит текст
        if "text" not in message or not message["text"]:
            raise HTTPException(status_code=400, detail="Сообщение должно содержать текст")
        
        # Отправляем сообщение через Telegram
        result = await send_message(
            int(current_user['id']),
            dialog_id,
            message["text"],
            message.get("reply_to")
        )
        
        return result
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