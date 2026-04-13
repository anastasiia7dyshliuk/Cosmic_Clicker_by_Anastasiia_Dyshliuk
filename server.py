from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import json
import os
import random
import threading
import time

# -------------------
# Налаштування сервера
# -------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'cosmic-clicker-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

DB_FILE = "players_db.json"

# -------------------
# Стан гри на сервері
# -------------------
game_state = {
    "stars": [],
    "players": {},
    "star_id_counter": 0,
    "running": True
}

# -------------------
# Робота з Базою Даних
# -------------------
def load_db():
    """Завантажує базу даних гравців з файлу"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db):
    """Зберігає базу даних гравців у файл"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def get_leaderboard():
    """Повертає таблицю лідерів (топ-10 гравців за рекордом)"""
    db = load_db()
    players = []
    for name, data in db.items():
        players.append({
            "name": name,
            "avatar": data.get("avatar", "👽"),
            "high_score": data.get("high_score", 0)
        })
    # Сортуємо за рекордом (від найбільшого до найменшого)
    players.sort(key=lambda p: p["high_score"], reverse=True)
    return players[:10]

# -------------------
# Генерація зірок на сервері
# -------------------
def spawn_stars():
    """Фоновий потік, який генерує зірки кожні 0.5-1 секунду"""
    while game_state["running"]:
        game_state["star_id_counter"] += 1
        star_id = game_state["star_id_counter"]

        # Визначаємо тип зірки
        if random.random() < 0.15:
            size = random.randint(25, 35)
            value = 2
            color = "cyan"
        else:
            size = random.randint(15, 25)
            value = 1
            color = "yellow"

        star = {
            "id": star_id,
            "x": random.randint(10, 880),
            "y": -50,
            "size": size,
            "speed": random.uniform(1, 3),
            "value": value,
            "color": color
        }

        game_state["stars"].append(star)

        # Відправляємо нову зірку всім підключеним гравцям
        socketio.emit("new_star", star)

        time.sleep(random.uniform(0.5, 1.0))

def move_stars_loop():
    """Фоновий потік, який рухає зірки вниз кожні 50мс"""
    while game_state["running"]:
        stars_to_remove = []
        for star in game_state["stars"]:
            star["y"] += star["speed"]
            if star["y"] > 900:
                stars_to_remove.append(star)

        for star in stars_to_remove:
            game_state["stars"].remove(star)
            socketio.emit("remove_star", {"id": star["id"]})

        # Відправляємо оновлені позиції всіх зірок
        socketio.emit("update_stars", game_state["stars"])
        time.sleep(0.05)

# -------------------
# Маршрути Flask
# -------------------
@app.route("/")
def index():
    """Головна сторінка гри"""
    return render_template("index.html")

# -------------------
# WebSocket події
# -------------------
@socketio.on("connect")
def handle_connect():
    """Гравець підключився"""
    print("Новий гравець підключився!")
    # Відправляємо поточний стан гри новому гравцю
    emit("game_state", {
        "stars": game_state["stars"],
        "leaderboard": get_leaderboard()
    })

@socketio.on("disconnect")
def handle_disconnect():
    """Гравець відключився"""
    print("Гравець відключився.")

@socketio.on("player_join")
def handle_player_join(data):
    """
    Гравець ввів нікнейм та обрав аватар.
    Зберігаємо його в базу даних та повертаємо його рекорд.
    """
    name = data.get("name", "Guest")
    avatar = data.get("avatar", "👽")

    db = load_db()
    if name in db:
        high_score = db[name]["high_score"]
        db[name]["avatar"] = avatar
    else:
        high_score = 0
        db[name] = {"high_score": 0, "avatar": avatar}
    save_db(db)

    # Зберігаємо гравця в стані сервера
    game_state["players"][name] = {
        "score": 0,
        "high_score": high_score,
        "avatar": avatar
    }

    # Відправляємо гравцю його дані та таблицю лідерів
    emit("player_data", {
        "name": name,
        "avatar": avatar,
        "high_score": high_score,
        "leaderboard": get_leaderboard()
    })

    # Повідомляємо всіх про нового гравця
    socketio.emit("leaderboard_update", get_leaderboard())

@socketio.on("catch_star")
def handle_catch_star(data):
    """
    Гравець зловив зірку.
    Перевіряємо, чи зірка ще існує (щоб два гравці не зловили одну зірку).
    """
    star_id = data.get("star_id")
    player_name = data.get("player_name")

    # Шукаємо зірку в стані гри
    caught_star = None
    for star in game_state["stars"]:
        if star["id"] == star_id:
            caught_star = star
            break

    if caught_star is None:
        # Зірку вже зловив інший гравець!
        emit("star_already_caught", {"star_id": star_id})
        return

    # Видаляємо зірку зі стану сервера
    game_state["stars"].remove(caught_star)

    # Оновлюємо рахунок гравця
    if player_name in game_state["players"]:
        game_state["players"][player_name]["score"] += caught_star["value"]
        current_score = game_state["players"][player_name]["score"]
        player_high_score = game_state["players"][player_name]["high_score"]

        # Перевірка на новий рекорд
        new_record = False
        if current_score > player_high_score:
            game_state["players"][player_name]["high_score"] = current_score
            db = load_db()
            if player_name in db:
                db[player_name]["high_score"] = current_score
                save_db(db)
            new_record = True

        # Відправляємо результат гравцю
        emit("star_caught_success", {
            "star_id": star_id,
            "value": caught_star["value"],
            "score": current_score,
            "high_score": game_state["players"][player_name]["high_score"],
            "new_record": new_record
        })

        # Повідомляємо всіх, що зірку зловлено
        socketio.emit("star_removed", {"star_id": star_id, "caught_by": player_name})

        # Оновлюємо таблицю лідерів для всіх
        if new_record:
            socketio.emit("leaderboard_update", get_leaderboard())

@socketio.on("reset_score")
def handle_reset_score(data):
    """Гравець натиснув 'Start again' — скидаємо його рахунок"""
    player_name = data.get("player_name")
    if player_name in game_state["players"]:
        game_state["players"][player_name]["score"] = 0
        emit("score_reset", {
            "score": 0,
            "high_score": game_state["players"][player_name]["high_score"]
        })

# -------------------
# Запуск сервера
# -------------------
if __name__ == "__main__":
    # Запускаємо фонові потоки для генерації та руху зірок
    star_thread = threading.Thread(target=spawn_stars, daemon=True)
    move_thread = threading.Thread(target=move_stars_loop, daemon=True)
    star_thread.start()
    move_thread.start()

    print("🌌 Cosmic Clicker Server запущено!")
    print("🌐 Відкрий http://localhost:5000 у браузері")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)