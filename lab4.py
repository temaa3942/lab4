import requests
import telebot

BOT_TOKEN = "8591210754:AAE5ZpQJzV2fIwmhAWBdMzP3xa8kX9a8AZU"
API_BASE = "https://restcountries.com/v3.1"

bot = telebot.TeleBot(BOT_TOKEN)


def get_country_by_name(name: str):
    url = f"{API_BASE}/name/{name}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except requests.RequestException:
        return None


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
        "/country <страна>\n\n"
        "Пример:\n"
        "/country Finland"
    )


@bot.message_handler(commands=["country"])
def country(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❗ Пример: /country Finland")
        return

    query = parts[1].strip()
    data = get_country_by_name(query)
    if not data:
        bot.send_message(message.chat.id, "❌ Страна не найдена или API недоступно")
        return

    c = data[0]
    name = c.get("name", {}).get("common", "—")
    capital = (c.get("capital") or ["—"])[0]
    population = c.get("population", 0)

    bot.send_message(
        message.chat.id,
        f"🏳️ {name}\n"
        f"Столица: {capital}\n"
        f"Население: {population:,}"
    )


print("Бот запущен...")
bot.infinity_polling()
