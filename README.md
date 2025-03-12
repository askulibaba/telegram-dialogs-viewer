# Telegram Dialogs Viewer

Веб-приложение для просмотра диалогов Telegram через авторизацию в боте.

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/askulibaba/enigma-telegram-app.git
cd enigma-telegram-app
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` со следующими параметрами:
```
BOT_TOKEN=ваш_токен_бота
API_ID=ваш_api_id
API_HASH=ваш_api_hash
```

## Запуск

```bash
python bot.py
```

## Использование

1. Откройте веб-приложение по адресу: https://askulibaba.github.io/enigma-telegram-app/login.html
2. Авторизуйтесь через Telegram
3. После успешной авторизации вы увидите список ваших диалогов

## Структура проекта

- `bot.py` - основной файл бота
- `docs/` - веб-интерфейс
  - `login.html` - страница авторизации
  - `chats.html` - страница с диалогами
- `sessions/` - директория для хранения сессий Telethon
- `.env` - конфигурация
- `requirements.txt` - зависимости проекта 