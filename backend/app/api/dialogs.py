from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.security import verify_token, TokenData
from app.services.telegram import get_dialogs, get_messages, send_message

router = APIRouter()

# Зависимость для проверки токена
async def get_current_user(token: str = Query(..., alias="token")) -> TokenData:
    """
    Проверяет токен и возвращает данные пользователя
    
    Args:
        token: JWT токен
        
    Returns:
        TokenData: Данные пользователя
    """
    token_data = verify_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data

class MessageRequest(BaseModel):
    """Запрос на отправку сообщения"""
    text: str
    reply_to: Optional[int] = None

@router.get("/", response_model=List[Dict[str, Any]])
async def get_dialogs_list(
    limit: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Получает список диалогов пользователя
    """
    try:
        # Получаем диалоги
        dialogs = await get_dialogs(current_user.user_id, limit)
        
        return dialogs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{dialog_id}/messages", response_model=List[Dict[str, Any]])
async def get_dialog_messages(
    dialog_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset_id: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Получает сообщения из диалога
    """
    try:
        # Получаем сообщения
        messages = await get_messages(
            current_user.user_id,
            dialog_id,
            limit,
            offset_id
        )
        
        return messages
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{dialog_id}/messages", response_model=Dict[str, Any])
async def send_dialog_message(
    dialog_id: int,
    message: MessageRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Отправляет сообщение в диалог
    """
    try:
        # Отправляем сообщение
        result = await send_message(
            current_user.user_id,
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