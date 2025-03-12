import os
import logging
import asyncio
from threading import Thread
from flask import Flask, send_from_directory, jsonify, request
from aiogram.utils import executor
from dotenv import load_dotenv
from bot import dp
from bot.utils import init_telegram_client, get_dialogs, verify_telegram_auth

# Загружаем переменные окружения
load_dotenv()

# Настройка уровня логирования в зависимости от переменной DEBUG
debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
log_level = logging.DEBUG if debug_mode else logging.INFO

# Настройка логирования
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if debug_mode:
    logger.debug("🔍 Режим отладки включен")

# Проверка конфигурации
required_vars = ['BOT_TOKEN', 'API_ID', 'API_HASH', 'APP_URL']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Отсутствуют необходимые переменные окружения: {', '.join(missing_vars)}")
    logger.error("Пожалуйста, добавьте их в настройках проекта на Railway или в файл .env")
    # Не выходим из программы, чтобы Railway не перезапускал приложение постоянно
    # Вместо этого продолжаем выполнение, но логируем ошибки

# Создаем директорию для сессий, если она не существует
os.makedirs('sessions', exist_ok=True)

# Инициализация Flask
app = Flask(__name__, static_folder='app/static', template_folder='app/templates')

# Хранилище для сессий и клиентов
sessions = {}
telegram_clients = {}

@app.route('/')
def index():
    """Главная страница"""
    return send_from_directory(app.template_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """Обработка статических файлов"""
    return send_from_directory(app.static_folder, path)

@app.route('/api/auth', methods=['POST'])
def auth():
    """Обработка авторизации через Telegram"""
    try:
        logger.info("Получен запрос на авторизацию")
        data = request.json
        logger.info(f"Данные авторизации: {data}")
        
        if verify_telegram_auth(os.getenv('BOT_TOKEN'), data):
            user_id = str(data.get('id'))
            logger.info(f"Пользователь {user_id} успешно авторизован")
            sessions[user_id] = {
                'auth_date': data.get('auth_date'),
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'username': data.get('username')
            }
            return jsonify({'success': True})
        logger.error("Ошибка верификации данных авторизации")
        return jsonify({'success': False, 'error': 'Invalid auth data'})
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dialogs', methods=['GET'])
async def get_dialogs_route():
    """Получение списка диалогов"""
    try:
        logger.info("Получен запрос на получение диалогов")
        user_id = request.args.get('user_id')
        logger.info(f"ID пользователя: {user_id}")
        
        if not user_id or user_id not in sessions:
            logger.error(f"Пользователь не авторизован: {user_id}")
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        logger.info(f"Сессии: {sessions}")
        
        # Инициализируем клиент, если его нет
        if user_id not in telegram_clients:
            logger.info(f"Инициализация клиента для пользователя {user_id}")
            try:
                client = await init_telegram_client(
                    user_id,
                    os.getenv('API_ID'),
                    os.getenv('API_HASH')
                )
                telegram_clients[user_id] = client
                logger.info(f"Клиент для пользователя {user_id} успешно инициализирован")
            except Exception as e:
                logger.error(f"Ошибка при инициализации клиента: {str(e)}", exc_info=True)
                return jsonify({'success': False, 'error': f"Ошибка инициализации: {str(e)}"})
        
        # Получаем диалоги
        logger.info(f"Получение диалогов для пользователя {user_id}")
        dialogs = await get_dialogs(telegram_clients[user_id])
        logger.info(f"Получено {len(dialogs)} диалогов")
        return jsonify({'success': True, 'dialogs': dialogs})
    except Exception as e:
        logger.error(f"Ошибка при получении диалогов: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

def run_flask():
    """Запуск Flask сервера"""
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        debug=debug_mode
    )

def run_bot():
    """Запуск бота"""
    executor.start_polling(dp, skip_updates=True)

if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Запускаем бота
    logger.info("🚀 Запуск бота и веб-сервера...")
    logger.info(f"Конфигурация:")
    logger.info(f"APP_URL: {os.getenv('APP_URL')}")
    logger.info(f"Режим отладки: {'Включен' if debug_mode else 'Выключен'}")
    
    run_bot() 