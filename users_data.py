
import json

DATA_FILE = "user_data.json"


def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"users": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def save_user_preferences(user_id, genre, movie, additional):
    data = load_data()
    data["users"][str(user_id)] = {
        "favorite_genre": genre,
        "favorite_movie": movie,
        "additional_preferences": additional
    }
    save_data(data)
