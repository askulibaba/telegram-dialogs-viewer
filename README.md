# Telegram Dialogs Viewer

Веб-приложение для просмотра диалогов Telegram с использованием Telegram Mini App.

## Описание

Это веб-приложение позволяет пользователям:
- Авторизоваться через Telegram
- Просматривать список своих диалогов в Telegram
- Видеть последние сообщения и непрочитанные сообщения

## Технологии

- Python 3.9+
- Flask (веб-сервер)
- aiogram (Telegram Bot API)
- Telethon (Telegram Client API)
- HTML5/CSS3/JavaScript (фронтенд)

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/telegram-dialogs-viewer.git
cd telegram-dialogs-viewer
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` и заполните его:
```
BOT_TOKEN=your_bot_token
API_ID=your_api_id
API_HASH=your_api_hash
APP_URL=https://your-app-name.up.railway.app
```

## Настройка на Railway

1. Создайте новый проект на Railway
2. Подключите GitHub репозиторий
3. Добавьте переменные окружения в настройках проекта
4. Дождитесь автоматического деплоя

## Структура проекта

```
├── app/
│   ├── static/         # Статические файлы (CSS, JS)
│   └── templates/      # HTML шаблоны
├── bot/
│   ├── __init__.py
│   ├── handlers.py     # Обработчики команд бота
│   └── utils.py        # Вспомогательные функции
├── sessions/           # Сессии Telegram
├── .env               # Переменные окружения
├── .gitignore        # Игнорируемые файлы
├── bot.py            # Основной файл бота
├── Procfile          # Конфигурация для Railway
├── README.md         # Документация
└── requirements.txt  # Зависимости проекта
```

## Разработка

Для локальной разработки:

1. Запустите бота:
```bash
python bot.py
```

2. Откройте веб-приложение через бота в Telegram

## Лицензия

MIT 