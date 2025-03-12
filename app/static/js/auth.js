const tg = window.Telegram.WebApp;
tg.expand();

// Функция для показа ошибки
function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    document.getElementById('loading').style.display = 'none';
}

// Функция для показа загрузки
function showLoading() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error').style.display = 'none';
}

// Функция обработки авторизации через Telegram
function onTelegramAuth(user) {
    console.log('Получены данные авторизации:', user);
    showLoading();
    
    if (!user || !user.id) {
        showError('Ошибка авторизации: не получены данные пользователя');
        return;
    }

    // Сохраняем данные авторизации
    localStorage.setItem('telegram_auth', JSON.stringify({
        ...user,
        auth_date: Math.floor(Date.now() / 1000)
    }));

    // Отправляем данные на сервер для верификации
    fetch('/api/auth', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(user)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Перенаправляем на страницу диалогов
            window.location.href = '/dialogs';
        } else {
            throw new Error(data.error || 'Ошибка авторизации');
        }
    })
    .catch(error => {
        console.error('Ошибка при верификации:', error);
        showError('Ошибка при верификации данных авторизации');
    });
}

// Проверяем, есть ли сохраненная сессия
const session = localStorage.getItem('telegram_auth');
if (session) {
    try {
        const sessionData = JSON.parse(session);
        const authDate = sessionData.auth_date;
        const now = Math.floor(Date.now() / 1000);
        
        // Проверяем срок действия сессии (24 часа)
        if (now - authDate < 86400) {
            window.location.href = '/dialogs';
        } else {
            localStorage.removeItem('telegram_auth');
            showError('Срок действия сессии истек. Пожалуйста, авторизуйтесь заново.');
        }
    } catch (e) {
        localStorage.removeItem('telegram_auth');
        showError('Ошибка при проверке сессии. Пожалуйста, авторизуйтесь заново.');
    }
}

// Обработка ошибок Telegram WebApp
tg.onEvent('error', function(error) {
    showError('Ошибка Telegram WebApp: ' + error);
}); 