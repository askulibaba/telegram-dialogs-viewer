# Telegram Dialogs Viewer Backend

Бэкенд для приложения Telegram Dialogs Viewer, которое позволяет просматривать и управлять диалогами Telegram через веб-интерфейс.

## Требования

- Python 3.9+
- FastAPI
- Telethon
- Другие зависимости из requirements.txt

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/telegram-dialogs-viewer.git
cd telegram-dialogs-viewer/backend
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл .env на основе .env.example:
```bash
cp .env.example .env
```

5. Отредактируйте файл .env, добавив свои данные:
```
SECRET_KEY=your_secret_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
BACKEND_CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]
```

## Запуск

Для запуска в режиме разработки:

```bash
uvicorn app.main:app --reload
```

Приложение будет доступно по адресу http://localhost:8000.

## API Endpoints

### Авторизация

- `POST /api/v1/auth/telegram` - Авторизация через Telegram Login Widget
- `POST /api/v1/auth/phone` - Отправка кода подтверждения на телефон
- `POST /api/v1/auth/code` - Авторизация по коду подтверждения

### Диалоги

- `GET /api/v1/dialogs` - Получение списка диалогов
- `GET /api/v1/dialogs/{dialog_id}/messages` - Получение сообщений из диалога
- `POST /api/v1/dialogs/{dialog_id}/messages` - Отправка сообщения в диалог

## Документация API

После запуска приложения документация API будет доступна по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Развертывание

Для развертывания в Docker:

```bash
docker build -t telegram-dialogs-viewer-backend .
docker run -p 8000:8000 --env-file .env telegram-dialogs-viewer-backend
```

## Лицензия

MIT 