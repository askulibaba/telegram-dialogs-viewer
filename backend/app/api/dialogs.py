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
        raise HTTPException(status_code=401, detail="Не указан токен авторизации")
    
    try:
        # Проверяем формат токена
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Неверный формат токена")
        
        # Проверяем токен
        token_data = verify_token(token)
        if not token_data:
            raise HTTPException(status_code=401, detail="Неверный токен авторизации")
        
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
        logger.info(f"Получение диалогов для пользователя {current_user['id']}")
        
        # Получаем диалоги из Telegram
        dialogs = await get_dialogs(int(current_user['id']))
        
        return dialogs
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