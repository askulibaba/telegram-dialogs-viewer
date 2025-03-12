const tg = window.Telegram.WebApp;
tg.expand();

function showError(message) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('dialogs').style.display = 'none';
    const errorElement = document.getElementById('error');
    errorElement.textContent = message;
    errorElement.style.display = 'block';
}

function showDialogs(dialogs) {
    document.getElementById('loading').style.display = 'none';
    
    if (!dialogs || dialogs.length === 0) {
        document.getElementById('no-dialogs').style.display = 'block';
        return;
    }

    const dialogsList = document.getElementById('dialogs');
    dialogsList.innerHTML = '';

    dialogs.forEach(dialog => {
        const li = document.createElement('li');
        li.className = 'dialog';

        const avatar = document.createElement('div');
        avatar.className = 'dialog-avatar';
        avatar.textContent = dialog.name.charAt(0).toUpperCase();

        const info = document.createElement('div');
        info.className = 'dialog-info';

        const name = document.createElement('div');
        name.className = 'dialog-name';
        name.textContent = dialog.name;

        const message = document.createElement('div');
        message.className = 'dialog-message';
        message.textContent = dialog.last_message || 'Нет сообщений';

        if (dialog.unread_count > 0) {
            const unreadBadge = document.createElement('div');
            unreadBadge.className = 'unread-badge';
            unreadBadge.textContent = dialog.unread_count;
            info.appendChild(unreadBadge);
        }

        info.appendChild(name);
        info.appendChild(message);
        li.appendChild(avatar);
        li.appendChild(info);
        dialogsList.appendChild(li);
    });

    dialogsList.style.display = 'block';
}

// Проверяем авторизацию
const session = localStorage.getItem('telegram_auth');
if (!session) {
    window.location.href = '/';
} else {
    try {
        const sessionData = JSON.parse(session);
        const authDate = sessionData.auth_date;
        const now = Math.floor(Date.now() / 1000);
        
        if (now - authDate > 86400) { // 24 часа
            localStorage.removeItem('telegram_auth');
            window.location.href = '/';
        } else {
            // Получаем диалоги
            fetch(`/api/dialogs?user_id=${sessionData.id}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showDialogs(data.dialogs);
                    } else {
                        throw new Error(data.error || 'Ошибка получения диалогов');
                    }
                })
                .catch(error => {
                    console.error('Ошибка при получении диалогов:', error);
                    showError('Ошибка при получении диалогов');
                });
        }
    } catch (e) {
        localStorage.removeItem('telegram_auth');
        window.location.href = '/';
    }
}

// Обработка ошибок Telegram WebApp
tg.onEvent('error', function(error) {
    showError('Ошибка: ' + error);
}); 