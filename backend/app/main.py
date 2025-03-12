import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api import auth, dialogs

# Создаем приложение FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Настраиваем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["auth"]
)
app.include_router(
    dialogs.router,
    prefix=f"{settings.API_V1_STR}/dialogs",
    tags=["dialogs"]
)

# Проверяем, существует ли директория для статических файлов
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # Подключаем статические файлы
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    """
    Корневой эндпоинт
    """
    return {
        "app_name": settings.APP_NAME,
        "version": "0.1.0",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health():
    """
    Проверка работоспособности
    """
    return {"status": "ok"} 