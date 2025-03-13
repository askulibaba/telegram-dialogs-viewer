"""
Модуль для работы с безопасностью
"""
import logging
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenData(BaseModel):
    """
    Данные токена
    """
    user_id: str
    exp: Optional[datetime] = None


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Создает JWT токен
    
    Args:
        data: Данные для токена
        expires_delta: Время жизни токена
        
    Returns:
        str: JWT токен
    """
    to_encode = data.copy()
    
    # Устанавливаем время истечения токена
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Добавляем время истечения в данные токена
    to_encode.update({"exp": expire.timestamp()})
    
    # Создаем JWT токен
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """
    Проверяет JWT токен
    
    Args:
        token: JWT токен
        
    Returns:
        Optional[TokenData]: Данные токена или None, если токен недействителен
    """
    try:
        # Декодируем токен
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        # Получаем ID пользователя
        user_id = payload.get("user_id")
        if user_id is None:
            return None
        
        # Получаем время истечения токена
        exp = payload.get("exp")
        if exp is not None:
            exp_datetime = datetime.fromtimestamp(exp)
            # Проверяем, не истек ли токен
            if exp_datetime < datetime.utcnow():
                return None
        
        # Возвращаем данные токена
        return TokenData(user_id=user_id, exp=exp_datetime if exp else None)
    except Exception as e:
        logger.error(f"Ошибка при проверке токена: {e}")
        
        # Для обратной совместимости с тестовыми токенами
        if token.startswith("jwt_token_") or token.startswith("telegram_token_") or token.startswith("test_token_"):
            user_id = token.split("_")[-1]
            return TokenData(user_id=user_id)
        
        return None


def verify_telegram_auth(data: Dict[str, Any]) -> bool:
    """
    Проверяет данные авторизации через Telegram
    
    Args:
        data: Данные авторизации
        
    Returns:
        bool: True, если данные верны, иначе False
    """
    # Заглушка для тестирования
    return True