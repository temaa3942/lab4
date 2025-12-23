import telebot

BOT_TOKEN = "8591210754:AAE5ZpQJzV2fIwmhAWBdMzP3xa8kX9a8AZU"
bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! 🌍\n"
        "Я бот по странам.\n"
        "Команды:\n"
        "/help — помощь"
    )


@bot.message_handler(commands=["help"])
def help_cmd(message):
    bot.send_message(
        message.chat.id,
        "📌 Команды:\n"
        "/start\n"
        "/help"
    )


print("Бот запущен...")
bot.infinity_polling()
