import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from googletrans import Translator, LANGUAGES
import asyncio
import os
from dotenv import load_dotenv

# ===== НАСТРОЙКИ =====
# Загружаем переменные из .env файла
load_dotenv()

# Получаем токен бота
TOKEN = os.getenv("BOT_TOKEN")

# Проверяем, что токен установлен
if not TOKEN:
    raise ValueError("Токен бота не найден! Проверьте файл .env")

DEFAULT_LANG = "en"       # Язык по умолчанию
MAX_RETRIES = 3           # Максимальное количество попыток перевода
CACHE_SIZE = 100          # Размер кэша переводов

# ===== ИНИЦИАЛИЗАЦИЯ БОТА =====
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ===== НАСТРОЙКА ПЕРЕВОДЧИКА =====
translator = Translator(service_urls=[
    'translate.google.com',
    'translate.google.ru',
    'translate.google.cn'
])

# ===== КЭШ ПЕРЕВОДОВ =====
translation_cache = {}
cache_keys = []

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'en'
        )
    """)
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else DEFAULT_LANG

def set_user_lang(user_id, lang):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, lang) 
        VALUES (?, ?)
    """, (user_id, lang))
    conn.commit()
    conn.close()

# ===== КЛАВИАТУРА =====
def language_keyboard():
    buttons = [
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_es"),
        InlineKeyboardButton(text="🇫🇷 Français", callback_data="lang_fr"),
        InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

# ===== ФУНКЦИИ ПЕРЕВОДА =====
def add_to_cache(text, dest, result):
    if len(cache_keys) >= CACHE_SIZE:
        del translation_cache[cache_keys.pop(0)]
    key = (text[:50], dest)  # Обрезаем текст для ключа
    translation_cache[key] = result
    cache_keys.append(key)

async def safe_translate(text, dest):
    # Проверяем кэш
    cache_key = (text[:50], dest)
    if cache_key in translation_cache:
        return translation_cache[cache_key]
    
    # Пробуем перевести с повторными попытками
    for attempt in range(MAX_RETRIES):
        try:
            result = translator.translate(text, dest=dest)
            add_to_cache(text, dest, result)
            return result
        except Exception as e:
            logging.warning(f"Попытка {attempt + 1} не удалась: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)
    
    raise Exception("Не удалось выполнить перевод после нескольких попыток")

# ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====
@dp.message(Command("start", "help"))
async def send_welcome(message: types.Message):
    user_lang = get_user_lang(message.from_user.id)
    lang_name = LANGUAGES.get(user_lang, user_lang).capitalize()
    
    text = (
        f"🤖 <b>Я бот-переводчик!</b>\n\n"
        f"Отправьте мне текст, и я переведу его на выбранный язык.\n"
        f"Текущий язык перевода: <b>{lang_name}</b>\n\n"
        f"Используйте кнопки ниже для смены языка."
    )
    await message.answer(text, reply_markup=language_keyboard())

@dp.message(Command("lang"))
async def show_languages(message: types.Message):
    await message.answer("Выберите язык перевода:", reply_markup=language_keyboard())

@dp.message()
async def handle_text(message: types.Message):
    try:
        user_lang = get_user_lang(message.from_user.id)
        text = message.text.strip()
        
        if not text:
            await message.answer("Пожалуйста, отправьте текст для перевода")
            return
            
        try:
            start_time = time.time()
            translated = await safe_translate(text, user_lang)
            trans_time = time.time() - start_time
            
            response = (
                f"🌍 <b>Оригинал</b>:\n{text}\n\n"
                f"🔁 <b>Перевод</b> ({LANGUAGES.get(user_lang, user_lang).capitalize()}):\n"
                f"{translated.text}\n\n"
                f"⏱ <i>Обработано за {trans_time:.1f} сек</i>"
            )
            await message.answer(response, reply_markup=language_keyboard())
            
        except Exception as e:
            logging.error(f"Ошибка перевода: {e}")
            await message.answer(
                "⚠ Не удалось выполнить перевод. Попробуйте:\n"
                "- Сократить текст\n"
                "- Попробовать позже\n"
                "- Сменить язык перевода (/lang)",
                reply_markup=language_keyboard()
            )
            
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("⚠ Произошла ошибка. Пожалуйста, попробуйте позже.")

@dp.callback_query(lambda call: call.data.startswith("lang_"))
async def change_language(call: types.CallbackQuery):
    try:
        lang_code = call.data.split("_")[1]
        lang_name = LANGUAGES.get(lang_code, lang_code).capitalize()
        
        set_user_lang(call.from_user.id, lang_code)
        await call.answer(f"Язык перевода изменён на {lang_name}", show_alert=True)
        
        # Обновляем сообщение
        await call.message.edit_text(
            f"Язык перевода установлен: <b>{lang_name}</b>\n\n"
            "Отправьте мне текст для перевода:",
            reply_markup=language_keyboard()
        )
        
    except Exception as e:
        logging.error(f"Ошибка смены языка: {e}")
        await call.answer("⚠ Ошибка при смене языка", show_alert=True)

# ===== ЗАПУСК БОТА =====
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    init_db()  # Инициализация базы данных
    
    logging.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())