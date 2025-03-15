import os
import secrets
from typing import List, Optional, Union, Any

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
    
    # URL приложения
    APP_URL: str = "https://web-production-921c.up.railway.app"
    
    # CORS настройки
    BACKEND_CORS_ORIGINS: Union[List[str], str] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str):
            # Если значение - строка в формате JSON-массива
            if v.startswith("[") and v.endswith("]"):
                try:
                    import json
                    return json.loads(v)
                except Exception:
                    pass
            
            # Если значение - строка с разделителями-запятыми
            return [i.strip() for i in v.split(",")]
        
        # Если значение уже список или другой тип
        return v
    
    # Настройки Telegram
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_API_URL: str = "https://api.telegram.org/bot"
    
    # Настройки бота
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Настройки JWT
    JWT_SECRET_KEY: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
    
    # Настройки Railway
    IS_RAILWAY: bool = os.environ.get("RAILWAY_ENVIRONMENT") is not None
    RAILWAY_VOLUME_NAME: Optional[str] = os.environ.get("RAILWAY_VOLUME_NAME")
    RAILWAY_VOLUME_MOUNT_PATH: Optional[str] = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/data")
    
    # Настройки сессий
    SESSIONS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sessions")
    
    class Config:
        case_sensitive = True
        env_file = ".env"


# Создаем экземпляр настроек
settings = Settings()

# Если приложение запущено на Railway и есть подключенный volume
if settings.IS_RAILWAY and settings.RAILWAY_VOLUME_MOUNT_PATH:
    # Используем путь к volume для хранения сессий
    sessions_path = os.path.join(settings.RAILWAY_VOLUME_MOUNT_PATH, "sessions")
    settings.SESSIONS_DIR = sessions_path
    
    # Создаем директорию, если она не существует
    os.makedirs(sessions_path, exist_ok=True)
    
    # Логируем информацию о настройках
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Приложение запущено на Railway с подключенным volume")
    logger.info(f"Имя volume: {settings.RAILWAY_VOLUME_NAME}")
    logger.info(f"Путь монтирования volume: {settings.RAILWAY_VOLUME_MOUNT_PATH}")
    logger.info(f"Путь к директории сессий: {settings.SESSIONS_DIR}") 