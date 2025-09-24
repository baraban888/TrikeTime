from flask import Flask, render_template, request, jsonify, send_from_directory, current_app
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения из .env (если файл есть)
load_dotenv()

app = Flask(__name__, template_folder="triketime-spa/dist", static_folder="triketime-spa/dist",static_url_path="")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback_secret_key")

# Разрешаем CORS (на будущее, если фронт будет обращаться к API)
CORS(app)

# ассеты Vite 
@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(app.static_folder + "/assets", filename)

# где лежит НОВЫЙ фронт
FRONT_DIR = "triketime-spa/public/triketime-beta"

app = Flask(__name__, static_folder=FRONT_DIR, template_folder=FRONT_DIR)

# на время разработки выключим кэш
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.cache = {}

@app.after_request
def no_cache(resp):
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

# ===== SPA-фолбэк =====
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def spa(path):
    # не перехватываем API
    if path.startswith('api/'):
        return "Not Found", 404
    # сначала пытаемся отдать статический файл (css/js/png)
    try:
        return send_from_directory(app.static_folder, path)
    except Exception:
        # иначе всегда index.html
        return send_from_directory(app.template_folder, 'index.html')

# service worker из той же папки
@app.route('/service-worker.js')
def service_worker():
    return send_from_directory(app.static_folder, 'service-worker.js',
                               mimetype='application/javascript')


@app.route("/api/ping", methods=["GET"])
def api_ping():
    return jsonify(ok=True), 200

@app.route("/api/history", methods=["GET"])
def api_history():
    rows = db_rows()  # используем твою функцию для выборки из базы
    data = [
        {"id": row[0], "start_time": row[1], "end_time": row[2]}
        for row in rows
    ]
    return jsonify(data), 200

# --- helpers ---
def _parse_dt(value):
    """Принимает ISO-строку, возвращает datetime или None.
       Если value=None — берём текущее время."""
    if value is None:
        return datetime.now().replace(microsecond=0)
    try:
        # поддержим и "2025-09-17 08:00:00", и "2025-09-17T08:00:00"
        return datetime.fromisoformat(value.replace("T", " ")).replace(microsecond=0)
    except Exception:
        return None


# --- API: создать смену ---
@app.route("/api/sessions", methods=["POST"])
def create_session():
    data = request.get_json(silent=True) or {}
    start_dt = _parse_dt(data.get("start_time"))
    end_dt   = _parse_dt(data.get("end_time"))

    if start_dt is None or end_dt is None:
        return jsonify(error="Invalid datetime. Use 'YYYY-MM-DD HH:MM:SS' or ISO 8601."), 422

    start_s = start_dt.isoformat(sep=" ")
    end_s   = end_dt.isoformat(sep=" ")

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO shifts (start_time, end_time) VALUES (?, ?)", (start_s, end_s))
        new_id = c.lastrowid
        conn.commit()

    return jsonify(id=new_id, start_time=start_s, end_time=end_s), 201

@app.route("/api/sessions/<int:session_id>", methods=["PUT"])
def update_session(session_id):
    data = request.get_json(silent=True) or {}

    # Разрешим обновлять одно или оба поля
    fields = []
    values = []

    if "start_time" in data:
        dt = _parse_dt(data["start_time"])
        if dt is None:
            return jsonify(error="Invalid start_time"), 422
        fields.append("start_time = ?")
        values.append(dt.isoformat(sep=" "))

    if "end_time" in data:
        dt = _parse_dt(data["end_time"])
        if dt is None:
            return jsonify(error="Invalid end_time"), 422
        fields.append("end_time = ?")
        values.append(dt.isoformat(sep=" "))

    if not fields:
        return jsonify(error="Nothing to update"), 400

    values.append(session_id)

    import sqlite3
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(f"UPDATE shifts SET {', '.join(fields)} WHERE id = ?", values)
        if c.rowcount == 0:
            return jsonify(error="Not found"), 404
        conn.commit()
        c.execute("SELECT id, start_time, end_time FROM shifts WHERE id = ?", (session_id,))
        row = c.fetchone()

    return jsonify({"id": row[0], "start_time": row[1], "end_time": row[2]}), 200

# API: удалить сессию
@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM shifts WHERE id = ?", (session_id,))
        conn.commit()

    return jsonify(ok=True, deleted_id=session_id), 200

# API: получить одну сессию
@app.route("/api/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, start_time, end_time FROM shifts WHERE id = ?", (session_id,))
        row = c.fetchone()

    if row is None:
        return jsonify(error="Session not found"), 404

    return jsonify({
        "id": row[0],
        "start_time": row[1],
        "end_time": row[2]
    }), 200

#_seed_one
if app.debug:

    @app.route("/api/_seed_one", methods=["POST"])
    def seed_one():
        import sqlite3, datetime
        with sqlite3.connect(DB_PATH) as conn:
         c = conn.cursor()
         now = datetime.datetime.now().replace(microsecond=0).isoformat(sep=" ")
         c.execute(
            "INSERT INTO shifts (start_time, end_time) VALUES (?, ?)",
            (now, now)
        )
        conn.commit()
        return jsonify(ok=True), 201

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



@app.route("/api/start_shift", methods=["POST"])
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


@app.route("/api/end_shift", methods=["POST"])
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


@app.route("/api/history", methods=["GET"])
def history():
    rows = db_rows(limit=10)
    return jsonify(rows)


@app.route("/api/clear_history", methods=["POST"])
def clear_history():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM shifts")
        conn.commit()
    return jsonify({"status": "cleared"})


@app.route("/api/download_history", methods=["GET"])
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
