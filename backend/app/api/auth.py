from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import hashlib
import hmac
import json
import time
import logging
import jwt
import os
from datetime import datetime, timedelta

from app.core.security import create_access_token, verify_telegram_auth
from app.services.telegram import send_code_request, sign_in, sign_in_2fa, get_session_info
from app.core.config import settings
from app.models.auth import (
    Token, User, PhoneAuthRequest, SignInRequest, 
    SignIn2FARequest, TelegramAuthRequest, ManualAuthRequest
)

router = APIRouter()

logger = logging.getLogger(__name__)

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
    temp_user_id: int
    phone_number: str
    code: str
    phone_code_hash: str
    password: Optional[str] = None

class AuthResponse(BaseModel):
    """Ответ на авторизацию"""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class SendCodeRequest(BaseModel):
    """Запрос на отправку кода подтверждения"""
    phone_number: str

class SendCodeResponse(BaseModel):
    """Ответ на запрос отправки кода"""
    temp_user_id: int
    phone_code_hash: str
    phone_number: str
    message: Optional[str] = None

class SignInRequest(BaseModel):
    """Запрос на авторизацию по коду"""
    temp_user_id: int
    phone_number: str
    code: str
    phone_code_hash: str

class SignIn2FARequest(BaseModel):
    """Запрос на авторизацию по коду с двухфакторной аутентификацией"""
    temp_user_id: int
    phone_number: str
    code: str
    phone_code_hash: str
    password: str

class ManualAuthRequest(BaseModel):
    """Запрос на ручную авторизацию (для тестирования)"""
    id: str
    first_name: Optional[str] = None
    username: Optional[str] = None

def verify_telegram_data(data: dict) -> bool:
    """
    Проверяет данные, полученные от Telegram Login Widget
    
    Args:
        data: Данные от Telegram Login Widget
    
    Returns:
        bool: True, если данные верны, иначе False
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    
    # Получаем хеш из данных
    received_hash = data.get('hash')
    if not received_hash:
        return False
    
    # Удаляем хеш из данных для проверки
    auth_data = data.copy()
    auth_data.pop('hash', None)
    
    # Сортируем данные по ключам
    data_check_string = '\n'.join([f'{k}={v}' for k, v in sorted(auth_data.items())])
    
    # Создаем секретный ключ из токена бота
    secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    
    # Создаем хеш для проверки
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    # Проверяем, совпадает ли хеш
    return computed_hash == received_hash

@router.post("/telegram")
async def telegram_auth(request: Request):
    """
    Обработчик авторизации через Telegram Login Widget
    """
    try:
        # Получаем данные запроса
        data = await request.json()
        
        # Для отладки
        print(f"Получены данные от Telegram: {data}")
        
        # Проверяем данные
        if not verify_telegram_data(data):
            # Для тестирования пропускаем проверку
            print("Внимание: Проверка данных Telegram отключена для тестирования")
            # return JSONResponse({"error": "Invalid data"}, status_code=400)
        
        # Проверяем, не устарели ли данные (не старше 24 часов)
        auth_date = data.get('auth_date', 0)
        current_time = int(time.time())
        if current_time - int(auth_date) > 86400:
            return JSONResponse({"error": "Authentication data is expired"}, status_code=400)
        
        # Создаем токен доступа (в реальном приложении здесь должна быть более сложная логика)
        user_id = data.get('id')
        access_token = f"telegram_token_{user_id}"
        
        # Возвращаем токен и данные пользователя
        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "first_name": data.get('first_name', ''),
                "last_name": data.get('last_name', ''),
                "username": data.get('username', ''),
                "photo_url": data.get('photo_url', '')
            }
        })
    except Exception as e:
        print(f"Ошибка при авторизации через Telegram: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/telegram")
async def telegram_auth_redirect(request: Request):
    """
    Обработчик редиректа после авторизации через Telegram
    """
    # Получаем параметры запроса
    params = dict(request.query_params)
    
    # Для отладки
    print(f"Получены параметры редиректа от Telegram: {params}")
    
    # Проверяем данные
    if not verify_telegram_data(params):
        # Для тестирования пропускаем проверку
        print("Внимание: Проверка данных Telegram отключена для тестирования")
        # return RedirectResponse(url=f"{settings.APP_URL}?error=invalid_data")
    
    # Создаем токен доступа
    user_id = params.get('id')
    access_token = f"telegram_token_{user_id}"
    
    # Перенаправляем пользователя на главную страницу с токеном
    return RedirectResponse(url=f"{settings.APP_URL}?token={access_token}&user_id={user_id}")

@router.post("/phone", response_model=Dict[str, Any])
async def phone_auth(auth_data: PhoneAuthRequest):
    """
    Отправка кода подтверждения на телефон
    """
    try:
        # Отправляем запрос на получение кода
        result = await send_code_request(auth_data.phone_number)
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/code", response_model=AuthResponse)
async def code_auth(auth_data: CodeAuthRequest):
    """
    Авторизация по коду подтверждения
    """
    try:
        # Авторизуемся
        user = await sign_in(
            auth_data.temp_user_id,
            auth_data.phone_number,
            auth_data.code,
            auth_data.phone_code_hash,
            auth_data.password
        )
        
        # Создаем токен доступа
        access_token = create_access_token({"sub": str(user["id"])})
        
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

@router.post("/send-code", response_model=SendCodeResponse)
async def send_code(request: SendCodeRequest):
    """
    Отправляет код подтверждения на указанный номер телефона
    """
    try:
        # Отправляем запрос на получение кода
        result = await send_code_request(request.phone_number)
        
        # Добавляем сообщение для пользователя
        result["message"] = f"Код подтверждения отправлен на номер {request.phone_number}"
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/sign-in", response_model=AuthResponse)
async def sign_in_with_code(request: SignInRequest):
    """
    Авторизация по коду подтверждения
    """
    try:
        # Авторизуемся по коду
        user_data = await sign_in(
            request.temp_user_id,
            request.phone_number,
            request.code,
            request.phone_code_hash
        )
        
        # Создаем токен
        user_id_str = str(user_data["id"])
        logger.info(f"Создаем токен для пользователя с ID: {user_id_str}")
        access_token = create_access_token({"user_id": user_id_str})
        
        logger.info(f"Токен успешно создан: {access_token[:10]}...")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }
    except ValueError as e:
        if "Требуется пароль двухфакторной аутентификации" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется пароль двухфакторной аутентификации"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/sign-in-2fa", response_model=AuthResponse)
async def sign_in_with_2fa(request: SignIn2FARequest):
    """
    Авторизация по коду подтверждения с двухфакторной аутентификацией
    """
    try:
        # Авторизуемся по коду и паролю
        user_data = await sign_in(
            request.temp_user_id,
            request.phone_number,
            request.code,
            request.phone_code_hash,
            request.password
        )
        
        # Создаем токен
        user_id_str = str(user_data["id"])
        logger.info(f"Создаем токен для пользователя с ID: {user_id_str}")
        access_token = create_access_token({"user_id": user_id_str})
        
        logger.info(f"Токен успешно создан: {access_token[:10]}...")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/manual", response_model=AuthResponse)
async def manual_auth(request: ManualAuthRequest):
    """
    Ручная авторизация для тестирования
    """
    try:
        # Создаем токен
        user_id_str = str(request.id)
        logger.info(f"Создаем токен для тестового пользователя с ID: {user_id_str}")
        access_token = create_access_token({"user_id": user_id_str})
        
        logger.info(f"Токен успешно создан: {access_token[:10]}...")
        
        # Формируем данные пользователя
        user_data = {
            "id": request.id,
            "first_name": request.first_name or "Test User",
            "username": request.username or "test_user"
        }
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/sessions", response_model=Dict[str, Any])
async def get_sessions_info(current_user: User = Depends(get_current_user)):
    """
    Получает информацию о сессиях пользователя для отладки
    """
    try:
        # Получаем информацию о сессии
        session_info = await get_session_info(current_user.id)
        
        return {
            "user_id": current_user.id,
            "session_info": session_info
        }
    except Exception as e:
        logging.error(f"Ошибка при получении информации о сессиях: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении информации о сессиях: {str(e)}"
        ) 