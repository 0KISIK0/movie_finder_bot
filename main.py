

import telebot
import requests
from dotenv import dotenv_values

from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from users_data import load_data, save_user_preferences

config = dotenv_values(".env")

API_TOKEN = config["API_TOKEN"]
KINOPOISK_TOKEN = config["KINOPOISK_TOKEN"]

API_URL = "https://api.kinopoisk.dev/v1.4/movie"

bot = telebot.TeleBot(API_TOKEN)
user_states = {}


def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("📋 Список команд"),
        KeyboardButton("🎬 Подобрать фильм")
    )
    markup.row(KeyboardButton("⚙️ Настройки"))
    return markup


def get_movies(genre):
    response = requests.get(
        API_URL,
        headers={"X-API-KEY": KINOPOISK_TOKEN},
        params={
            "genres.name": genre,
            "page": 1,
            "limit": 5,
            "sortField": "rating.kp",
            "sortType": "-1"
        },
        timeout=10
    )
    return response.json().get("docs", [])


def show_movies(chat_id, genre):
    movies = get_movies(genre)

    if not movies:
        bot.send_message(chat_id, "Фильмы не найдены.")
        return

    for movie in movies:
        name = movie.get("name", "Без названия")
        year = movie.get("year", "Не указан")
        rating = movie.get("rating", {}).get("kp", "Нет рейтинга")
        description = movie.get("description", "Описание отсутствует")

        bot.send_message(
            chat_id,
            f"🎬 {name}\n"
            f"📅 Год: {year}\n"
            f"⭐ Рейтинг: {rating}\n"
            f"🎭 Жанр: {genre}\n\n"
            f"📖 Описание:\n{description}"
        )


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Я помогу тебе выбрать фильм 🎬",
        reply_markup=main_menu()
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "/start — главное меню\n"
        "/help — список команд\n"
        "/find — поиск фильма\n"
        "/genre — фильмы по жанру\n"
        "/set_preferences — сохранить предпочтения\n"
        "/recommend_movie — персональные рекомендации"
    )


@bot.message_handler(commands=["set_preferences"])
def set_preferences(message):
    user_states[message.chat.id] = {"step": 1}
    bot.send_message(message.chat.id, "Какой твой любимый жанр?")


@bot.message_handler(commands=["recommend_movie"])
def recommend_movie(message):
    data = load_data()
    user = data["users"].get(str(message.chat.id), {})
    genre = user.get("favorite_genre", "")

    if genre:
        show_movies(message.chat.id, genre)
    else:
        bot.send_message(
            message.chat.id,
            "Сначала сохрани предпочтения: /set_preferences"
        )


@bot.message_handler(commands=["genre"])
def genre(message):
    user_states[message.chat.id] = {"step": "genre"}
    bot.send_message(message.chat.id, "Введи жанр фильма:")


@bot.message_handler(commands=["find"])
def find(message):
    user_states[message.chat.id] = {"step": "find"}
    bot.send_message(message.chat.id, "Введи название фильма:")


@bot.message_handler(func=lambda m: m.text == "📋 Список команд")
def menu_help(message):
    help_command(message)


@bot.message_handler(func=lambda m: m.text == "🎬 Подобрать фильм")
def menu_recommend(message):
    recommend_movie(message)


@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def menu_settings(message):
    set_preferences(message)


@bot.message_handler(content_types=["text"])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id not in user_states:
        return

    state = user_states[chat_id]

    if state["step"] == "find":
        del user_states[chat_id]

        response = requests.get(
            "https://api.kinopoisk.dev/v1.4/movie/search",
            headers={"X-API-KEY": KINOPOISK_TOKEN},
            params={"query": text, "limit": 1},
            timeout=10
        )

        movies = response.json().get("docs", [])

        if movies:
            movie = movies[0]
            bot.send_message(
                chat_id,
                f"🎬 {movie.get('name', 'Без названия')}\n"
                f"📅 Год: {movie.get('year', 'Не указан')}\n"
                f"⭐ Рейтинг: {movie.get('rating', {}).get('kp', 'Нет рейтинга')}\n"
                f"📖 {movie.get('description', 'Нет описания')}"
            )
        else:
            bot.send_message(chat_id, "Фильм не найден.")

    elif state["step"] == "genre":
        del user_states[chat_id]
        show_movies(chat_id, text)

    elif state["step"] == 1:
        state["genre"] = text
        state["step"] = 2
        bot.send_message(chat_id, "Какой твой любимый фильм?")

    elif state["step"] == 2:
        state["movie"] = text
        state["step"] = 3
        bot.send_message(chat_id, "Дополнительные пожелания? Напиши «нет», если их нет.")

    elif state["step"] == 3:
        additional = "" if text.lower() == "нет" else text
        save_user_preferences(
            chat_id,
            state["genre"],
            state["movie"],
            additional
        )

        del user_states[chat_id]
        bot.send_message(chat_id, "✅ Предпочтения сохранены!", reply_markup=main_menu())


if __name__ == "__main__":
    bot.infinity_polling()
