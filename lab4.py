import re
import requests
import telebot
from telebot import types

# ТОКЕН ТГ
BOT_TOKEN = "8591210754:AAE5ZpQJzV2fIwmhAWBdMzP3xa8kX9a8AZU"
# Базовый адрес REST Countries API
API_BASE = "https://restcountries.com/v3.1"

# Создаем объект Telegram-бота
bot = telebot.TeleBot(BOT_TOKEN)

LIST_PAGE_SIZE = 20
_countries_cache = None  # сюда кэшируем список стран 


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


def get_all_countries_names():
    """
    Получение списка всех стран.
    Нужно translations, чтобы показать русское название рядом с английским.
    """
    return api_get_json(f"{API_BASE}/all?fields=name,translations")


def _prepare_countries_list(raw_list):
    """
    Превращает ответ API в список кортежей (en, ru).
    ru берется из translations.rus.common, если есть.
    """
    out = []
    if not isinstance(raw_list, list):
        return out

    for c in raw_list:
        en = c.get("name", {}).get("common", "—")

        translations = c.get("translations") or {}
        ru = "—"
        if isinstance(translations, dict):
            rus = translations.get("rus") or {}
            if isinstance(rus, dict):
                ru = rus.get("common") or rus.get("official") or "—"

        out.append((en, ru))

    # сортировка по английскому
    out.sort(key=lambda x: (x[0] or "").lower())
    return out


def _build_list_text(page: int, items):
    total = len(items)
    if total == 0:
        return "Список стран пуст."

    pages = (total + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE
    if page < 0:
        page = 0
    if page > pages - 1:
        page = pages - 1

    start = page * LIST_PAGE_SIZE
    end = min(start + LIST_PAGE_SIZE, total)

    lines = [f"📄 Список стран (страница {page + 1}/{pages})\n"]
    for i in range(start, end):
        en, ru = items[i]
        lines.append(f"{i + 1}. {en} — {ru}")

    return "\n".join(lines)


def _build_list_keyboard(page: int, total_items: int):
    pages = (total_items + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE
    kb = types.InlineKeyboardMarkup()

    prev_page = page - 1
    next_page = page + 1

    btns = []
    if prev_page >= 0:
        btns.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"list:{prev_page}"))
    if next_page < pages:
        btns.append(types.InlineKeyboardButton("Вперёд ▶️", callback_data=f"list:{next_page}"))

    if btns:
        kb.row(*btns)
    return kb


def _send_or_edit_list(chat_id=None, message_id=None, page=0):
    global _countries_cache

    # грузим кэш один раз
    if _countries_cache is None:
        raw = get_all_countries_names()
        if raw in ("NETWORK_ERROR", "API_ERROR") or raw is None:
            text = "⚠️ Не удалось получить список стран. Попробуй позже."
            if message_id:
                bot.edit_message_text(text, chat_id, message_id)
            else:
                bot.send_message(chat_id, text)
            return
        _countries_cache = _prepare_countries_list(raw)

    text = _build_list_text(page, _countries_cache)
    kb = _build_list_keyboard(page, len(_countries_cache))

    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    else:
        bot.send_message(chat_id, text, reply_markup=kb)


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


# ОБРАБОТЧИКИ КОМАНД
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
        "/list — список стран \n"
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
        "/country <country> - информация о стране \n"
        "/list  - список стран "
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


@bot.message_handler(commands=["list"])
def list_cmd(message):
    """
    /list — выводит список стран (English — Русский) с кнопками листания
    """
    _send_or_edit_list(chat_id=message.chat.id, page=0)


@bot.callback_query_handler(func=lambda call: call.data.startswith("list:"))
def list_callback(call):
    """
    Обработчик кнопок для /list
    """
    try:
        page = int(call.data.split(":", 1)[1])
    except Exception:
        page = 0

    _send_or_edit_list(chat_id=call.message.chat.id, message_id=call.message.message_id, page=page)
    bot.answer_callback_query(call.id)


print("Бот запущен...")
bot.infinity_polling()
