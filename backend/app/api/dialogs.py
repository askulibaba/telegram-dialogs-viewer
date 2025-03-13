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
        
        # Здесь должна быть проверка токена
        # В данном случае просто проверяем, что токен не пустой
        if not token:
            raise HTTPException(status_code=401, detail="Токен не может быть пустым")
        
        # Извлекаем ID пользователя из токена
        # В реальном приложении здесь должна быть проверка JWT
        if token.startswith("test_token_"):
            user_id = token.split("_")[-1]
        else:
            user_id = "unknown"
        
        return {"id": user_id}
    except Exception as e:
        logger.error(f"Ошибка при проверке токена: {e}")
        raise HTTPException(status_code=401, detail="Неверный токен авторизации")

# Эндпоинт для получения списка диалогов
@router.get("/", response_model=List[Dialog])
async def get_dialogs(current_user = Depends(get_current_user)):
    """
    Получает список диалогов пользователя
    """
    logger.info(f"Получение диалогов для пользователя {current_user['id']}")
    
    # В реальном приложении здесь должен быть запрос к API Telegram
    # В данном случае возвращаем тестовые данные
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    dialogs = [
        Dialog(
            id="1",
            title="Тестовый диалог 1",
            last_message="Привет! Как дела?",
            last_message_date=now.isoformat(),
            unread_count=2
        ),
        Dialog(
            id="2",
            title="Тестовый диалог 2",
            last_message="Посмотри это видео!",
            last_message_date=yesterday.isoformat(),
            unread_count=0
        ),
        Dialog(
            id="3",
            title="Тестовый диалог 3",
            last_message="Спасибо за информацию",
            last_message_date=(now - timedelta(days=2)).isoformat(),
            unread_count=0
        )
    ]
    
    return dialogs

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

@router.get("/{dialog_id}/messages", response_model=List[Dict[str, Any]])
async def get_dialog_messages(dialog_id: str, current_user = Depends(get_current_user)):
    """
    Получает сообщения из диалога
    """
    logger.info(f"Получение сообщений из диалога {dialog_id} для пользователя {current_user['id']}")
    
    # Вызываем сервис для получения сообщений
    messages = await get_messages(dialog_id, current_user['id'])
    
    return messages

@router.post("/{dialog_id}/messages", response_model=Dict[str, Any])
async def send_dialog_message(dialog_id: str, message: Dict[str, Any], current_user = Depends(get_current_user)):
    """
    Отправляет сообщение в диалог
    """
    logger.info(f"Отправка сообщения в диалог {dialog_id} от пользователя {current_user['id']}")
    
    if 'text' not in message:
        raise HTTPException(status_code=400, detail="Текст сообщения обязателен")
    
    # Вызываем сервис для отправки сообщения
    result = await send_message(dialog_id, message['text'], current_user['id'])
    
    return result 