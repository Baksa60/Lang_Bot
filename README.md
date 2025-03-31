# Telegram Translation Bot

🤖 Бот-переводчик на базе Google Translate API

## Функции
- Перевод текста на выбранный язык
- Поддержка 5 языков (можно расширить)
- Кэширование запросов
- Устойчивость к ошибкам

## Установка
1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш-username/translator-bot.git
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` и добавьте токен бота:
```
BOT_TOKEN=ваш_токен
```

4. Запустите бота:
```bash
python bot.py
```

## Настройка
Чтобы добавить новые языки, измените функцию `language_keyboard()` в файле `bot.py`

## Лицензия
MIT
