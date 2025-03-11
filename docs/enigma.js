// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Алфавит для шифрования
const ALPHABET = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ';

// Класс ротора Энигмы
class Rotor {
    constructor(wiring, notch) {
        this.wiring = wiring;
        this.notch = notch;
        this.position = 0;
    }

    forward(char) {
        const idx = ALPHABET.indexOf(char);
        const shifted = (idx + this.position) % ALPHABET.length;
        const encoded = this.wiring[shifted];
        return ALPHABET[(ALPHABET.indexOf(encoded) - this.position + ALPHABET.length) % ALPHABET.length];
    }

    backward(char) {
        const idx = ALPHABET.indexOf(char);
        const shifted = (idx + this.position) % ALPHABET.length;
        const encodedIdx = this.wiring.indexOf(ALPHABET[shifted]);
        return ALPHABET[(encodedIdx - this.position + ALPHABET.length) % ALPHABET.length];
    }

    rotate() {
        this.position = (this.position + 1) % ALPHABET.length;
        return this.position === this.notch;
    }
}

// Создание роторов с разными настройками
function createRotors(key) {
    const rotor1 = new Rotor([...ALPHABET].sort(() => Math.random() - 0.5).join(''), 
        ALPHABET.indexOf(key[0]));
    const rotor2 = new Rotor([...ALPHABET].sort(() => Math.random() - 0.5).join(''), 
        ALPHABET.indexOf(key[1]));
    const rotor3 = new Rotor([...ALPHABET].sort(() => Math.random() - 0.5).join(''), 
        ALPHABET.indexOf(key[2]));
    
    // Установка начальных позиций роторов
    rotor1.position = ALPHABET.indexOf(key[3]);
    rotor2.position = ALPHABET.indexOf(key[4]);
    rotor3.position = 0;

    return [rotor1, rotor2, rotor3];
}

// Рефлектор
const reflector = {};
for (let i = 0; i < ALPHABET.length; i += 2) {
    reflector[ALPHABET[i]] = ALPHABET[i + 1];
    reflector[ALPHABET[i + 1]] = ALPHABET[i];
}

// Функция шифрования одного символа
function encryptChar(char, rotors) {
    if (!ALPHABET.includes(char)) return char;

    // Вращение роторов
    if (rotors[0].rotate()) {
        if (rotors[1].rotate()) {
            rotors[2].rotate();
        }
    }

    // Прямой проход через роторы
    let result = char;
    for (const rotor of rotors) {
        result = rotor.forward(result);
    }

    // Отражение
    result = reflector[result];

    // Обратный проход через роторы
    for (const rotor of rotors.reverse()) {
        result = rotor.backward(result);
    }
    rotors.reverse();

    return result;
}

// Функция шифрования текста
function encrypt() {
    const inputText = document.getElementById('inputText').value.toUpperCase();
    const key = document.getElementById('key').value.toUpperCase();

    if (key.length !== 5) {
        tg.showPopup({
            title: 'Ошибка',
            message: 'Пожалуйста, введите ключ из 5 букв русского алфавита',
            buttons: [{text: 'OK'}]
        });
        return;
    }

    if (![...key].every(char => ALPHABET.includes(char))) {
        tg.showPopup({
            title: 'Ошибка',
            message: 'Ключ должен содержать только буквы русского алфавита',
            buttons: [{text: 'OK'}]
        });
        return;
    }

    const rotors = createRotors(key);
    let result = '';

    for (const char of inputText) {
        result += encryptChar(char, rotors);
    }

    document.getElementById('result').value = result;
    
    // Показываем кнопку "Поделиться" после шифрования
    document.getElementById('shareButton').style.display = 'block';
    
    // Вибрация при завершении шифрования
    if (tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
    }
}

// Функция для отправки результата в Telegram
function shareResult() {
    const result = document.getElementById('result').value;
    if (result) {
        tg.sendData(JSON.stringify({
            action: 'share',
            text: result
        }));
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Настраиваем цвета и тему
    document.body.style.backgroundColor = tg.backgroundColor;
    
    // Скрываем кнопку "Поделиться" изначально
    document.getElementById('shareButton').style.display = 'none';
    
    // Добавляем обработчик для ввода ключа
    document.getElementById('key').addEventListener('input', function(e) {
        this.value = this.value.replace(/[^А-Яа-яЁё]/g, '').toUpperCase();
    });
    
    // Настраиваем основную кнопку Telegram
    if (tg.MainButton) {
        tg.MainButton.setText('ЗАШИФРОВАТЬ');
        tg.MainButton.onClick(encrypt);
    }
}); 