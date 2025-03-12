import os
import secrets
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, BaseSettings, validator


class Settings(BaseSettings):
    """
    Настройки приложения
    """
    # Основные настройки
    APP_NAME: str = "Telegram Dialogs Viewer"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
    
    # CORS настройки
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Telegram настройки
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    
    # Настройки сессий
    SESSIONS_DIR: str = "sessions"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


# Создаем экземпляр настроек
settings = Settings()

# Создаем директорию для сессий, если она не существует
os.makedirs(settings.SESSIONS_DIR, exist_ok=True) 