from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import create_access_token, verify_telegram_auth
from app.services.telegram import (
    get_or_create_client, 
    is_user_authorized, 
    send_code_request, 
    sign_in
)

router = APIRouter()

class TelegramAuthRequest(BaseModel):
    """Запрос на авторизацию через Telegram Login Widget"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

class PhoneAuthRequest(BaseModel):
    """Запрос на отправку кода подтверждения"""
    phone_number: str

class CodeAuthRequest(BaseModel):
    """Запрос на авторизацию по коду"""
    phone_number: str
    code: str
    phone_code_hash: str
    password: Optional[str] = None

class AuthResponse(BaseModel):
    """Ответ на авторизацию"""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

@router.post("/telegram-auth", response_model=AuthResponse)
async def telegram_auth(auth_data: TelegramAuthRequest):
    """
    Авторизация через Telegram Login Widget
    """
    # Проверяем данные авторизации
    if not verify_telegram_auth(auth_data.dict()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные данные авторизации"
        )
    
    # Создаем токен доступа
    access_token = create_access_token(auth_data.id)
    
    # Формируем ответ
    return {
        "access_token": access_token,
        "user": {
            "id": auth_data.id,
            "first_name": auth_data.first_name,
            "last_name": auth_data.last_name,
            "username": auth_data.username,
            "photo_url": auth_data.photo_url
        }
    }

@router.post("/phone-auth", response_model=Dict[str, Any])
async def phone_auth(auth_data: PhoneAuthRequest):
    """
    Отправка кода подтверждения на телефон
    """
    try:
        # Генерируем временный ID пользователя
        temp_user_id = f"temp_{auth_data.phone_number}"
        
        # Отправляем запрос на получение кода
        result = await send_code_request(temp_user_id, auth_data.phone_number)
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/code-auth", response_model=AuthResponse)
async def code_auth(auth_data: CodeAuthRequest):
    """
    Авторизация по коду подтверждения
    """
    try:
        # Генерируем временный ID пользователя
        temp_user_id = f"temp_{auth_data.phone_number}"
        
        # Авторизуемся
        user = await sign_in(
            temp_user_id,
            auth_data.phone_number,
            auth_data.code,
            auth_data.phone_code_hash,
            auth_data.password
        )
        
        # Создаем токен доступа
        access_token = create_access_token(user["id"])
        
        # Формируем ответ
        return {
            "access_token": access_token,
            "user": user
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 