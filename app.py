from flask import Flask, render_template, request, jsonify, send_from_directory, current_app
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения из .env (если файл есть)
load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback_secret_key")

# Разрешаем CORS (на будущее, если фронт будет обращаться к API)
CORS(app)

DB_PATH = "database.db"
# Главная страница
@app.route('/',endpoint='home')
def home():
    return render_template('index.html')

# Отдаём сервис-воркер из корня
@app.route('/service-worker.js')
def service_worker():
    return send_from_directory(current_app.root_path, 'service-worker.js', mimetype='application/javascript')


# ---------- БАЗА ДАННЫХ ----------
# ---------- БАЗА ДАННЫХ ----------
DB_PATH = "database.db"

def init_db():
    """Создаёт таблицу, если её ещё нет."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT,
                end_time   TEXT
            )
        """)
        conn.commit()

def db_rows(limit=None):
    """Возвращает список смен (последние сверху)."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        sql = "SELECT id, start_time, end_time FROM shifts ORDER BY id DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        c.execute(sql)
        return c.fetchall()

init_db()
# ----------------------------------

# ----------------------------------


# ---------- РОУТЫ ----------



@app.route("/start_shift", methods=["POST"])
def start_shift():
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO shifts (start_time, end_time) VALUES (?, ?)",
            (start_time, None),
        )
        conn.commit()
    return jsonify({"status": "started", "start_time": start_time})


@app.route("/end_shift", methods=["POST"])
def end_shift():
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE shifts SET end_time = ? WHERE end_time IS NULL",
            (end_time,),
        )
        conn.commit()
    return jsonify({"status": "ended", "end_time": end_time})


@app.route("/history", methods=["GET"])
def history():
    rows = db_rows(limit=10)
    return jsonify(rows)


@app.route("/clear_history", methods=["POST"])
def clear_history():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM shifts")
        conn.commit()
    return jsonify({"status": "cleared"})


@app.route("/download_history", methods=["GET"])
def download_history():
    rows = db_rows()
    # Готовим CSV (первая строка — заголовки)
    csv_data = "id,start_time,end_time\n"
    for row in rows:
        csv_data += f"{row[0]},{row[1]},{row[2]}\n"

    return (
        csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": 'attachment; filename="history.csv"',
        },
    )
# ---------------------------


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
