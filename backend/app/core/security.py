import hmac
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenData(BaseModel):
    """
    Данные токена
    """
    user_id: int
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
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
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
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
        exp = payload.get("exp")
        
        if user_id is None:
            return None
        
        token_data = TokenData(user_id=user_id, exp=datetime.fromtimestamp(exp))
        
        return token_data
    except Exception:
        return None


def verify_telegram_auth(auth_data: Dict[str, Any]) -> bool:
    """
    Проверяет данные аутентификации Telegram
    
    Args:
        auth_data: Данные аутентификации
        
    Returns:
        bool: True, если данные верны, иначе False
    """
    # Проверяем, что данные не устарели (не более 1 дня)
    auth_date = int(auth_data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        return False
    
    # Получаем хеш из данных
    received_hash = auth_data.pop("hash", None)
    if not received_hash:
        return False
    
    # Создаем строку для проверки
    data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(auth_data.items())])
    
    # Создаем секретный ключ
    secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    
    # Вычисляем хеш
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Сравниваем хеши
    return computed_hash == received_hash