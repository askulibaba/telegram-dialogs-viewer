document.addEventListener('DOMContentLoaded', function() {
    // Элементы интерфейса
    const authSection = document.getElementById('auth-section');
    const dialogsSection = document.getElementById('dialogs-section');
    const dialogsList = document.getElementById('dialogs-list');
    const loadingElement = document.getElementById('loading');
    const errorElement = document.getElementById('error-message');
    const telegramLoginButton = document.getElementById('telegram-login');
    const logoutButton = document.getElementById('logout-button');

    // Базовый URL API
    const API_BASE_URL = '/api/v1';

    // Проверяем, авторизован ли пользователь
    function checkAuth() {
        const token = localStorage.getItem('access_token');
        if (token) {
            // Если есть токен, пытаемся загрузить диалоги
            showDialogsSection();
            fetchDialogs();
        } else {
            // Если нет токена, показываем секцию авторизации
            showAuthSection();
        }
    }

    // Показать секцию авторизации
    function showAuthSection() {
        if (authSection) authSection.style.display = 'block';
        if (dialogsSection) dialogsSection.style.display = 'none';
    }

    // Показать секцию с диалогами
    function showDialogsSection() {
        if (authSection) authSection.style.display = 'none';
        if (dialogsSection) dialogsSection.style.display = 'block';
    }

    // Показать сообщение об ошибке
    function showError(message) {
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }
    }

    // Скрыть сообщение об ошибке
    function hideError() {
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }

    // Показать индикатор загрузки
    function showLoading() {
        if (loadingElement) {
            loadingElement.style.display = 'block';
        }
    }

    // Скрыть индикатор загрузки
    function hideLoading() {
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    }

    // Загрузить диалоги
    async function fetchDialogs() {
        showLoading();
        hideError();

        const token = localStorage.getItem('access_token');
        if (!token) {
            hideLoading();
            showAuthSection();
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/dialogs/`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    // Если токен недействителен, показываем секцию авторизации
                    localStorage.removeItem('access_token');
                    showAuthSection();
                    throw new Error('Необходима авторизация');
                }
                throw new Error('Ошибка при загрузке диалогов');
            }

            const data = await response.json();
            renderDialogs(data);
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoading();
        }
    }

    // Отрисовать диалоги
    function renderDialogs(dialogs) {
        if (!dialogsList) return;

        dialogsList.innerHTML = '';

        if (!dialogs || dialogs.length === 0) {
            dialogsList.innerHTML = '<p class="no-dialogs">Диалоги не найдены</p>';
            return;
        }

        dialogs.forEach(dialog => {
            const dialogElement = document.createElement('div');
            dialogElement.className = 'dialog-card';

            const unreadBadge = dialog.unread_count > 0 
                ? `<span class="unread-badge">${dialog.unread_count}</span>` 
                : '';

            dialogElement.innerHTML = `
                <div class="dialog-header">
                    <div class="dialog-avatar" style="background-image: url('${dialog.photo || ''}')"></div>
                    <div class="dialog-name">${dialog.name}${unreadBadge}</div>
                </div>
                <div class="dialog-last-message">${dialog.last_message || 'Нет сообщений'}</div>
                <div class="dialog-time">${formatDate(dialog.last_message_date)}</div>
            `;

            dialogsList.appendChild(dialogElement);
        });
    }

    // Форматировать дату
    function formatDate(dateString) {
        if (!dateString) return '';

        const date = new Date(dateString);
        const now = new Date();
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);

        // Если сегодня
        if (date.toDateString() === now.toDateString()) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        // Если вчера
        else if (date.toDateString() === yesterday.toDateString()) {
            return 'Вчера';
        }
        // Иначе показываем дату
        else {
            return date.toLocaleDateString();
        }
    }

    // Обработчик авторизации через Telegram
    function handleTelegramAuth(user) {
        // Отправляем данные на сервер для проверки
        fetch(`${API_BASE_URL}/auth/telegram`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(user)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Ошибка авторизации');
            }
            return response.json();
        })
        .then(data => {
            // Сохраняем токен
            localStorage.setItem('access_token', data.access_token);
            // Показываем диалоги
            showDialogsSection();
            fetchDialogs();
        })
        .catch(error => {
            showError(error.message);
        });
    }

    // Обработчик выхода
    function handleLogout() {
        localStorage.removeItem('access_token');
        showAuthSection();
    }

    // Инициализация Telegram Login Widget
    if (telegramLoginButton) {
        // Здесь должен быть код для инициализации виджета Telegram Login
        // Обычно это скрипт, который добавляется на страницу
    }

    // Обработчик кнопки выхода
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    }

    // Инициализация приложения
    checkAuth();

    // Экспортируем функции для использования в глобальном контексте
    window.telegramLogin = handleTelegramAuth;
}); 