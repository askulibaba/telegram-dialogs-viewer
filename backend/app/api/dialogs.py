from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from pydantic import BaseModel
import random
from datetime import datetime, timedelta

from app.core.security import verify_token, TokenData
from app.services.telegram import get_dialogs, get_messages, send_message

router = APIRouter()

# Тестовые данные для диалогов
SAMPLE_DIALOGS = [
    {
        "id": 1,
        "title": "Иван Иванов",
        "last_message": "Привет, как дела?",
        "last_message_date": (datetime.now() - timedelta(minutes=5)).strftime("%H:%M"),
        "unread_count": 2
    },
    {
        "id": 2,
        "title": "Мария Петрова",
        "last_message": "Спасибо за информацию!",
        "last_message_date": (datetime.now() - timedelta(hours=1)).strftime("%H:%M"),
        "unread_count": 0
    },
    {
        "id": 3,
        "title": "Группа проекта",
        "last_message": "Встреча завтра в 10:00",
        "last_message_date": (datetime.now() - timedelta(days=1)).strftime("%d.%m"),
        "unread_count": 5
    }
]

def verify_token(authorization: Optional[str] = Header(None)):
    """
    Проверяет токен авторизации
    
    Args:
        authorization: Заголовок Authorization
    
    Returns:
        str: ID пользователя
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Не указан токен авторизации")
    
    # Проверяем формат токена
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Неверный формат токена")
    
    token = parts[1]
    
    # Для тестирования просто проверяем, что токен не пустой
    if not token:
        raise HTTPException(status_code=401, detail="Пустой токен")
    
    # В реальном приложении здесь должна быть проверка токена
    # и получение ID пользователя из токена
    
    # Для тестирования извлекаем ID из токена
    if token.startswith("telegram_token_"):
        user_id = token.replace("telegram_token_", "")
    elif token.startswith("test_token_"):
        user_id = token.replace("test_token_", "")
    else:
        user_id = "unknown"
    
    return user_id

@router.get("/", response_model=List[Dict[str, Any]])
async def get_dialogs(user_id: str = Depends(verify_token)):
    """
    Получение списка диалогов пользователя
    
    Args:
        user_id: ID пользователя (из токена)
    
    Returns:
        List[Dict[str, Any]]: Список диалогов
    """
    # В реальном приложении здесь должен быть запрос к Telegram API
    # для получения диалогов пользователя
    
    # Для тестирования возвращаем тестовые данные
    # Добавляем случайные значения для разнообразия
    dialogs = SAMPLE_DIALOGS.copy()
    
    # Добавляем случайные диалоги
    for i in range(random.randint(1, 3)):
        dialogs.append({
            "id": 100 + i,
            "title": f"Тестовый диалог {i+1}",
            "last_message": f"Сообщение {random.randint(1, 100)}",
            "last_message_date": (datetime.now() - timedelta(hours=random.randint(1, 24))).strftime("%H:%M"),
            "unread_count": random.randint(0, 10)
        })
    
    return dialogs

@router.get("/{dialog_id}/messages", response_model=List[Dict[str, Any]])
async def get_messages(dialog_id: int, user_id: str = Depends(verify_token)):
    """
    Получение сообщений диалога
    
    Args:
        dialog_id: ID диалога
        user_id: ID пользователя (из токена)
    
    Returns:
        List[Dict[str, Any]]: Список сообщений
    """
    # В реальном приложении здесь должен быть запрос к Telegram API
    # для получения сообщений диалога
    
    # Для тестирования возвращаем тестовые данные
    messages = []
    for i in range(10):
        is_outgoing = random.choice([True, False])
        messages.append({
            "id": i + 1,
            "text": f"Тестовое сообщение {i+1}",
            "date": (datetime.now() - timedelta(minutes=i*10)).strftime("%H:%M"),
            "is_outgoing": is_outgoing,
            "sender": "Вы" if is_outgoing else "Собеседник"
        })
    
    return messages

class MessageRequest(BaseModel):
    """Запрос на отправку сообщения"""
    text: str
    reply_to: Optional[int] = None

@router.post("/{dialog_id}/messages", response_model=Dict[str, Any])
async def send_dialog_message(
    dialog_id: int,
    message: MessageRequest,
    current_user: TokenData = Depends(verify_token)
):
    """
    Отправляет сообщение в диалог
    """
    try:
        # Отправляем сообщение
        result = await send_message(
            current_user,
            dialog_id,
            message.text,
            message.reply_to
        )
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 