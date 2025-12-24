import re
import requests
import telebot

BOT_TOKEN = "8591210754:AAE5ZpQJzV2fIwmhAWBdMzP3xa8kX9a8AZU"
API_BASE = "https://restcountries.com/v3.1"

bot = telebot.TeleBot(BOT_TOKEN)


def api_get_json(url: str):
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
    return api_get_json(f"{API_BASE}/name/{name}")


def get_countries_by_language(lang: str):
    return api_get_json(f"{API_BASE}/lang/{lang}")


def format_country(c: dict) -> str:
    name = c.get("name", {}).get("common", "—")
    official = c.get("name", {}).get("official", name)
    capital = (c.get("capital") or ["—"])[0]
    region = c.get("region", "—")
    subregion = c.get("subregion", "—")
    population = c.get("population", 0)
    timezones = ", ".join(c.get("timezones") or []) or "—"

    currencies = c.get("currencies") or {}
    currency_list = []
    if isinstance(currencies, dict):
        for code, meta in currencies.items():
            nm = meta.get("name") if isinstance(meta, dict) else ""
            currency_list.append(f"{code} ({nm})" if nm else code)
    currency_text = ", ".join(currency_list) if currency_list else "—"

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


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! 🌍\n"
        "Команды:\n"
        "/country <страна> — информация о стране\n"
        "/help — помощь"
    )


@bot.message_handler(commands=["help"])
def help_cmd(message):
    bot.send_message(
        message.chat.id,
        "📌 Команды:\n"
        "/country <страна>\n"
        "Примеры:\n"
        "/country Finland\n"
    )


@bot.message_handler(commands=["country"])
def country(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(message.chat.id, "❗ Укажи страну. Пример: /country Finland")
        return

    query = parts[1].strip()
    data = get_countries_by_name(query)

    if data == "NETWORK_ERROR":
        bot.send_message(message.chat.id, "⚠️ Ошибка сети. Попробуй позже.")
        return
    if data == "API_ERROR":
        bot.send_message(message.chat.id, "⚠️ Ошибка сервиса API. Попробуй позже.")
        return
    if not data or not isinstance(data, list):
        bot.send_message(message.chat.id, "❌ Страна не найдена.")
        return

    bot.send_message(message.chat.id, format_country(data[0]))


print("Бот запущен...")
bot.infinity_polling()
