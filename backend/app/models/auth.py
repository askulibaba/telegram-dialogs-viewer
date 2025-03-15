from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class User(BaseModel):
    """
    Модель пользователя
    """
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None


class Token(BaseModel):
    """
    Модель токена доступа
    """
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Данные токена
    """
    user_id: str
    exp: Optional[float] = None


class PhoneAuthRequest(BaseModel):
    """
    Запрос на отправку кода подтверждения
    """
    phone_number: str


class SignInRequest(BaseModel):
    """
    Запрос на авторизацию по коду
    """
    temp_user_id: int
    phone_number: str
    code: str
    phone_code_hash: str


class SignIn2FARequest(BaseModel):
    """
    Запрос на авторизацию по коду с двухфакторной аутентификацией
    """
    temp_user_id: int
    phone_number: str
    code: str
    phone_code_hash: str
    password: str


class TelegramAuthRequest(BaseModel):
    """
    Запрос на авторизацию через Telegram Login Widget
    """
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class ManualAuthRequest(BaseModel):
    """
    Запрос на ручную авторизацию (для тестирования)
    """
    id: str
    first_name: Optional[str] = None
    username: Optional[str] = None 