import tkinter as tk
import random
import json
import os
import re

# -------------------
# Глобальні змінні та Налаштування
# -------------------
score = 0
high_score = 0
stars = []
game_running = False
game_started = False

DB_FILE = "players_db.json"
player_name = "Player"
player_avatar = "👽"
selected_avatar = "👽"
record_notified = False

AVATARS = ['👽', '🚀', '👨‍🚀', '👾', '🤖', '🛸', '☄️', '🌟', '🌙']
avatar_buttons = []


# -------------------
# Робота з Базою Даних
# -------------------
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)


# -------------------
# Функції гри
# -------------------
def catch_star(event):
    """Обробка звичайного лівого кліку (Single Left-Click)"""
    global score, high_score, record_notified
    if not game_running:
        return
    for star in stars:
        x1, y1, x2, y2 = canvas.coords(star["id"])
        if x1 <= event.x <= x2 and y1 <= event.y <= y2:
            score += star.get("value", 1)
            show_bonus(event.x, event.y, star.get("value", 1))
            canvas.delete(star["id"])
            stars.remove(star)

            # Скидаємо курсор на звичайний після видалення зірки
            canvas.config(cursor="")

            if score > high_score:
                high_score = score

                db = load_db()
                db[player_name]["high_score"] = high_score
                save_db(db)

                if not record_notified and high_score > 0:
                    record_notified = True
                    show_record_alarm()

            update_labels()
            break


def show_bonus(x, y, value):
    bonus = canvas.create_text(x, y, text=f"+{value}", fill="white",
                               font=("Arial", 20, "bold"))
    canvas.after(500, lambda: canvas.delete(bonus))


def show_record_alarm():
    canvas_width = canvas.winfo_width() or 900
    canvas_height = canvas.winfo_height() or 900
    alarm = canvas.create_text(canvas_width / 2, canvas_height / 2,
                               text=f"🚨 NEW RECORD, {player_name}! 🚨",
                               fill="cyan", font=("Arial", 36, "bold"))
    canvas.after(3000, lambda: canvas.delete(alarm))


def update_labels():
    score_label.config(text=f"Score: {score}")
    high_score_label.config(text=f"Your High Score: {high_score}")


def spawn_star():
    if not game_running:
        return
    canvas_width = canvas.winfo_width() or 900

    # ЗМЕНШЕНО РОЗМІР ЗІРОК
    size = random.randint(15, 25)
    x = random.randint(10, canvas_width - size - 10)
    y = -50

    if random.random() < 0.15:
        size = random.randint(25, 35)  # Рідкісна зірка трохи більша
        value = 2
        color = "cyan"
    else:
        value = 1
        color = "yellow"

    # Додаємо тег "star", щоб відслідковувати наведення курсору
    star_id = canvas.create_oval(x, y, x + size, y + size, fill=color, outline="", tags="star")
    speed = random.uniform(1, 3)
    stars.append({"id": star_id, "speed": speed, "value": value})

    root.after(random.randint(300, 800), spawn_star)


def move_stars():
    global score, high_score
    if not game_running:
        return
    for star in stars[:]:
        canvas.move(star["id"], 0, star["speed"])
        x1, y1, x2, y2 = canvas.coords(star["id"])
        if y2 > canvas.winfo_height():
            canvas.delete(star["id"])
            stars.remove(star)
            canvas.config(cursor="")

    update_labels()
    root.after(50, move_stars)


# -------------------
# Навігація та Керування
# -------------------
def select_avatar(av, btn):
    global selected_avatar
    selected_avatar = av
    for b in avatar_buttons:
        b.config(bg="#ffc0cb", relief="flat")
    btn.config(bg="#40E0D0", relief="sunken")


def confirm_nickname():
    global player_name, player_avatar, high_score

    entered_name = name_entry.get().strip()

    # ПЕРЕВІРКА УМОВ ВВОДУ НІКНЕЙМУ
    if not entered_name or len(entered_name) > 15 or not re.match(r'^[A-Za-z0-9 ]+$', entered_name):
        error_label.config(text="Please reread the username entry conditions and try again.")
        return

    error_label.config(text="")

    player_name = entered_name
    player_avatar = selected_avatar

    db = load_db()
    if player_name in db:
        high_score = db[player_name]["high_score"]
        db[player_name]["avatar"] = player_avatar
    else:
        high_score = 0
        db[player_name] = {
            "high_score": high_score,
            "avatar": player_avatar
        }
    save_db(db)

    avatar_label.config(text=player_avatar)
    name_label.config(text=player_name)
    update_labels()

    start_screen_frame.pack_forget()
    canvas.pack(fill="both", expand=True)

    player_info_frame.place(relx=0.03, rely=0.03, anchor="nw")
    hud_frame.place(relx=0.5, rely=0.03, anchor="n")
    instructions_label.place(relx=0.5, rely=0.85, anchor="s")


def start_game():
    global game_running, game_started, record_notified
    game_started = True
    game_running = True
    record_notified = False

    action_btn.config(text="Stop game", command=stop_game, bg="#ff66cc", fg="white")
    spawn_star()
    move_stars()


def stop_game():
    global game_running
    game_running = False
    action_btn.config(text="Start again", command=restart_game, bg="#40E0D0", fg="black")


def restart_game():
    global score, game_running, record_notified
    score = 0
    record_notified = False
    for star in stars[:]:
        canvas.delete(star["id"])
    stars.clear()
    update_labels()

    game_running = True
    action_btn.config(text="Stop game", command=stop_game, bg="#ff66cc", fg="white")
    spawn_star()
    move_stars()


def exit_game():
    """Закриває гру"""
    root.destroy()


# -------------------
# Вікно та UI
# -------------------
root = tk.Tk()
root.title("Cosmic Clicker 🌌")
root.geometry("900x900")
root.minsize(600, 600)
root.configure(bg="#000000")

# --- ВІКНО 1: Екран вводу нікнейму та вибору аватара ---
start_screen_frame = tk.Frame(root, bg="#ffc0cb")
start_screen_frame.pack(fill="both", expand=True)

tk.Label(start_screen_frame, text="Welcome to Cosmic Clicker!", font=("Arial", 28, "bold"), bg="#ffc0cb").pack(pady=40)

tk.Label(start_screen_frame, text="Enter your nickname:", font=("Arial", 18, "bold"), bg="#ffc0cb").pack(pady=(10, 0))
tk.Label(start_screen_frame, text="(English letters only, max 15 characters)", font=("Arial", 12, "italic"),
         bg="#ffc0cb", fg="#333333").pack(pady=(0, 10))

name_entry = tk.Entry(start_screen_frame, font=("Arial", 18), justify="center")
name_entry.pack(pady=5)

error_label = tk.Label(start_screen_frame, text="", font=("Arial", 12, "bold"), bg="#ffc0cb", fg="red")
error_label.pack(pady=5)

tk.Label(start_screen_frame, text="Choose your avatar:", font=("Arial", 18), bg="#ffc0cb").pack(pady=(10, 5))
avatar_frame = tk.Frame(start_screen_frame, bg="#ffc0cb")
avatar_frame.pack(pady=10)


def create_avatar_btn(av):
    # ЗБІЛЬШЕНО width=3 та додано padx=5, щоб емодзі не обрізались
    btn = tk.Button(avatar_frame, text=av, font=("Arial", 24), bg="#ffc0cb", relief="flat", cursor="hand2", width=3,
                    padx=5)
    btn.config(command=lambda: select_avatar(av, btn))
    btn.pack(side="left", padx=5)
    avatar_buttons.append(btn)
    return btn


for av in AVATARS:
    create_avatar_btn(av)

if avatar_buttons:
    select_avatar(AVATARS[0], avatar_buttons[0])

buttons_frame = tk.Frame(start_screen_frame, bg="#ffc0cb")
buttons_frame.pack(pady=30)

confirm_btn = tk.Button(buttons_frame, text="Confirm", font=("Arial", 20, "bold"),
                        bg="#40E0D0", fg="black", command=confirm_nickname, width=10, cursor="hand2")
confirm_btn.pack(side="left", padx=10)

exit_btn_start = tk.Button(buttons_frame, text="Exit", font=("Arial", 20, "bold"),
                           bg="#ff4d4d", fg="white", command=exit_game, width=10, cursor="hand2")
exit_btn_start.pack(side="left", padx=10)

# --- ВІКНО 2: Ігрове поле (Canvas) ---
canvas = tk.Canvas(root, bg="#000000", highlightthickness=0)

# Звичайний лівий клік для лову зірок (<Button-1>)
canvas.bind("<Button-1>", catch_star)

# Зміна курсору при наведенні на зірку (тег "star")
canvas.tag_bind("star", "<Enter>", lambda e: canvas.config(cursor="crosshair"))
canvas.tag_bind("star", "<Leave>", lambda e: canvas.config(cursor=""))

# --- UI: Профіль Гравця (Зліва зверху) ---
player_info_frame = tk.Frame(root, bg="#1a1a1a", bd=2, relief="ridge", padx=10, pady=5)

avatar_label = tk.Label(player_info_frame, text="👽", font=("Arial", 32), bg="#1a1a1a", fg="white")
avatar_label.pack(side="left", padx=(0, 10))

name_label = tk.Label(player_info_frame, text="Player", font=("Arial", 16, "bold"), bg="#1a1a1a", fg="#40E0D0")
name_label.pack(side="left")

# --- UI: HUD-панель (По центру зверху) ---
hud_frame = tk.Frame(root, bg="#000000")

high_score_label = tk.Label(hud_frame, text=f"Your High Score: {high_score}",
                            font=("Arial", 20, "bold"), bg="#000000", fg="#ffc0cb")
high_score_label.pack()

score_label = tk.Label(hud_frame, text=f"Score: {score}",
                       font=("Arial", 20), bg="#000000", fg="white")
score_label.pack()

game_buttons_frame = tk.Frame(hud_frame, bg="#000000")
game_buttons_frame.pack(pady=5)

action_btn = tk.Button(game_buttons_frame, text="Start", font=("Arial", 14, "bold"),
                       command=start_game, bg="#40E0D0", fg="black", width=12, cursor="hand2")
action_btn.pack(side="left", padx=5)

exit_btn_game = tk.Button(game_buttons_frame, text="Exit", font=("Arial", 14, "bold"),
                          command=exit_game, bg="#ff4d4d", fg="white", width=12, cursor="hand2")
exit_btn_game.pack(side="left", padx=5)

# --- UI: Інструкція на ігровому екрані (Знизу по центру) ---
instructions_label = tk.Label(root, text="⭐ Left-click on a star to catch it! ⭐",
                              font=("Arial", 16, "bold"), bg="#000000", fg="#ffff99")

root.mainloop()
