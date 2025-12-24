import re
import requests
import telebot

#ТОКЕН ТГ
BOT_TOKEN = "8591210754:AAE5ZpQJzV2fIwmhAWBdMzP3xa8kX9a8AZU"
# Базовый адрес REST Countries API
API_BASE = "https://restcountries.com/v3.1"

# Создаем объект Telegram-бота
bot = telebot.TeleBot(BOT_TOKEN)

# ФУНКЦИИ ДЛЯ РАБОТЫ С API
def api_get_json(url: str):
    """
    Делает GET-запрос к REST Countries API и возвращает:
    - list/dict (JSON), если запрос успешен
    - None, если 404 (ничего не найдено)
    - "API_ERROR", если сервер вернул другую ошибку (например 500)
    - "NETWORK_ERROR", если проблема с сетью/таймаутом
    """
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            return "API_ERROR"
        return r.json()
    except requests.RequestException:
        return "NETWORK_ERROR"
    

def get_countries_by_name(name: str):
    """
    Получение информации о стране по названию:
    GET https://restcountries.com/v3.1/name/{countryName}
    """
    return api_get_json(f"{API_BASE}/name/{name}")


# ФОРМАТИРОВАНИЕ ОТВЕТА

def format_country(c: dict) -> str:
    """
    Преобразует JSON-объект страны в удобный текст для сообщения в Telegram.
    Если каких-то данных нет — выводит "—".
    """
    name = c.get("name", {}).get("common", "—")
    official = c.get("name", {}).get("official", name)

    # capital в API обычно список, поэтому берем первый элемент
    capital = (c.get("capital") or ["—"])[0]

    region = c.get("region", "—")
    subregion = c.get("subregion", "—")

    population = c.get("population", 0)

    # timezones — список строк
    timezones = ", ".join(c.get("timezones") or []) or "—"

    # currencies в v3.1 — словарь: код -> {name, symbol}
    currencies = c.get("currencies") or {}
    currency_list = []
    if isinstance(currencies, dict):
        for code, meta in currencies.items():
            nm = meta.get("name") if isinstance(meta, dict) else ""
            currency_list.append(f"{code} ({nm})" if nm else code)
    currency_text = ", ".join(currency_list) if currency_list else "—"

    # languages — словарь: код -> название
    languages = c.get("languages") or {}
    language_text = ", ".join(languages.values()) if isinstance(languages, dict) and languages else "—"

    return (
        f"🏳️ {name}\n"
        f"Официальное: {official}\n"
        f"Столица: {capital}\n"
        f"Регион: {region} / {subregion}\n"
        f"Население: {population:,}\n"
        f"Валюты: {currency_text}\n"
        f"Языки: {language_text}\n"
        f"Часовые пояса: {timezones}"
    )


# =========================
# ОБРАБОТЧИКИ КОМАНД TELEGRAM
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    """
    /start — приветствие и подсказка по командам.
    """
    bot.send_message(
        message.chat.id,
        "Привет! 🌍\n"
        "Я бот со справочной информацией по странам (REST Countries API).\n\n"
        "Команды:\n"
        "/country <страна> — информация о стране\n"
        "/help — помощь"
    )


@bot.message_handler(commands=["help"])
def help_cmd(message):
    """
    /help — инструкция по использованию.
    """
    bot.send_message(
        message.chat.id,
        "📌 Команды:\n"
        "/country <страна>\n\n"
        "Примеры:\n"
        "/country Finland\n"
        "/country Japan"
    )


@bot.message_handler(commands=["country"])
def country(message):
    """
    /country <название> — основная команда:
    - проверяет ввод
    - делает запрос к API
    - обрабатывает ошибки
    - выводит данные по первой найденной стране
    """
    parts = message.text.split(maxsplit=1)

    # Проверка наличия аргумента
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(message.chat.id, "❗ Укажи страну. Пример: /country Finland")
        return

    query = parts[1].strip()
    data = get_countries_by_name(query)

    # Обработка сетевых и серверных ошибок
    if data == "NETWORK_ERROR":
        bot.send_message(message.chat.id, "⚠️ Ошибка сети. Попробуй позже.")
        return
    if data == "API_ERROR":
        bot.send_message(message.chat.id, "⚠️ Ошибка сервиса API. Попробуй позже.")
        return

    # Если ничего не найдено
    if not data or not isinstance(data, list):
        bot.send_message(message.chat.id, "❌ Страна не найдена.")
        return

    # Выводим информацию по первой найденной стране
    bot.send_message(message.chat.id, format_country(data[0]))

from telebot import types

# =========================
# /list С КНОПКАМИ
# =========================

COUNTRIES_CACHE = {}   # chat_id -> list of country names
PAGE_SIZE = 20         # сколько стран на странице


def build_list_keyboard(page: int, total_pages: int):
    """
    Создаёт inline-клавиатуру для листания списка стран
    """
    kb = types.InlineKeyboardMarkup()
    buttons = []

    if page > 0:
        buttons.append(
            types.InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"list:{page-1}"
            )
        )

    if page < total_pages - 1:
        buttons.append(
            types.InlineKeyboardButton(
                text="➡️ Вперёд",
                callback_data=f"list:{page+1}"
            )
        )

    if buttons:
        kb.row(*buttons)

    return kb


@bot.message_handler(commands=["list"])
def list_countries(message):
    """
    /list — выводит список стран с кнопками навигации
    """
    data = api_get_json(f"{API_BASE}/all")

    if data == "NETWORK_ERROR":
        bot.send_message(message.chat.id, "⚠️ Ошибка сети. Попробуй позже.")
        return
    if data == "API_ERROR":
        bot.send_message(message.chat.id, "⚠️ Ошибка сервиса API. Попробуй позже.")
        return
    if not data or not isinstance(data, list):
        bot.send_message(message.chat.id, "❌ Не удалось получить список стран.")
        return
    print("REST Countries status:", data.status_code)

    # Сохраняем список стран в кэше
    names = [c.get("name", {}).get("common", "—") for c in data]
    COUNTRIES_CACHE[message.chat.id] = names

    page = 0
    total_pages = (len(names) + PAGE_SIZE - 1) // PAGE_SIZE

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = names[start:end]

    text = (
        f"🌍 Список стран (страница {page+1}/{total_pages}):\n"
        + "\n".join(chunk)
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=build_list_keyboard(page, total_pages)
    )
    

@bot.callback_query_handler(func=lambda call: call.data.startswith("list:"))
def list_callback(call):
    """
    Обработка нажатий кнопок 'Назад / Вперёд'
    """
    page = int(call.data.split(":")[1])
    names = COUNTRIES_CACHE.get(call.message.chat.id)

    if not names:
        bot.answer_callback_query(call.id, "Список устарел. Введите /list заново.")
        return

    total_pages = (len(names) + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = names[start:end]

    text = (
        f"🌍 Список стран (страница {page+1}/{total_pages}):\n"
        + "\n".join(chunk)
    )

    bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=build_list_keyboard(page, total_pages)
    )

    bot.answer_callback_query(call.id)

print("Бот запущен...")
bot.infinity_polling()
