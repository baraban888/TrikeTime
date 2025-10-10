from flask import Flask, render_template, request, jsonify, send_from_directory, current_app, make_response
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload
from db import engine, SessionLocal, create_tables
from models import Base, User, Shift, RefreshToken
from auth import register_user, login_user, require_auth, make_access, make_refresh, verify_refresh, set_refresh_cookie, clear_refresh_cookie

# Загружаем переменные окружения из .env (если файл есть)
load_dotenv()
create_tables()

# ---------- БАЗА ДАННЫХ ----------
DB_PATH = "database.db"

# где лежит НОВЫЙ фронт
FRONT_DIR = "triketime-spa/public/triketime-beta"

app = Flask(__name__, static_folder=FRONT_DIR, template_folder=FRONT_DIR)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback_secret_key")

@app.post("/api/login")
def api_login():
    data = request.get_json(force=True)
    # login_user возвращал токен — теперь вернём пользователя и проверим пароль тут
    username, password = data.get("username"), data.get("password")
    with SessionLocal() as s:
        u = s.scalar(select(User).where(User.username == username, User.is_active == True))
        from passlib.hash import bcrypt
        if not u or not bcrypt.verify(password, u.password_hash):
            return {"ok": False, "error": "bad_credentials"}, 401

        access = make_access(u)
        refresh, jti, _ = make_refresh(u, s)

        resp = make_response({"ok": True, "access": access, "role": u.role})
        set_refresh_cookie(resp, refresh)
        return resp

@app.post("/api/refresh")
def api_refresh():
    rt_cookie = request.cookies.get("rt")
    if not rt_cookie:
        return {"ok": False, "error": "no_refresh"}, 401
    with SessionLocal() as s:
        claims = verify_refresh(rt_cookie, s)
        if not claims:
            return {"ok": False, "error": "invalid_refresh"}, 401

        # Ротация: помечаем старый refresh как отозванный и выдаём новый
        s.execute(update(RefreshToken).where(RefreshToken.jti == claims["jti"]).values(revoked=True))
        user = s.get(User, int(claims["sub"]))
        access = make_access(user)
        new_refresh, new_jti, _ = make_refresh(user, s)

        resp = make_response({"ok": True, "access": access})
        set_refresh_cookie(resp, new_refresh)
        return resp

@app.post("/api/logout")
def api_logout():
    rt_cookie = request.cookies.get("rt")
    with SessionLocal() as s:
        if rt_cookie:
            claims = verify_refresh(rt_cookie, s)
            if claims:
                s.execute(update(RefreshToken).where(RefreshToken.jti == claims["jti"]).values(revoked=True))
                s.commit()
    resp = make_response({"ok": True})
    clear_refresh_cookie(resp)
    return resp
# Разрешаем CORS (на будущее, если фронт будет обращаться к API)
ALLOWED = [o.strip() for o in os.getenv("ALLOWED_ORIGINS","").split(",") if o.strip()]
# Разрешаем cookie (refresh) и заголовок Authorization (access)
CORS(
    app,
    resources={r"/api/*": {"origins": ALLOWED}},
    supports_credentials=True,
    expose_headers=["Content-Type", "Authorization"],
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"]
)

# ассеты Vite 
@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(app.static_folder + "/assets", filename)

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
    return send_from_directory(os.path.dirname(__file__), 'service-worker.js',
                               mimetype='application/javascript')


@app.route("/api/ping", methods=["GET"])
def api_ping():
    return jsonify(ok=True), 200

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
# добавь в app.py (если ещё не добавлял)

    @app.route("/api/seed_one", methods=["POST"])
    def seed_one():
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO shifts(start_time, end_time) VALUES(?, ?)",
                (now.isoformat(), (now+timedelta(minutes=15)).isoformat()))
            conn.commit()
        return jsonify(ok=True), 201
def db_rows(limit=None):

         """Возвращает список смен (последние сверху)."""
         with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            sql = "SELECT id, start_time, end_time FROM shifts ORDER BY id DESC"
            if limit:
                sql += f" LIMIT {int(limit)}"
            c.execute(sql)
            return c.fetchall()

# -------- РОУТЫ --------

def now_iso():
    # единый формат UTC-штампа
    return datetime.now(timezone.utc).isoformat()

def get_open_shift(conn):
    """Возвращает открытую смену (end_time IS NULL) или None."""
    r = conn.execute(
        "SELECT id, start_time FROM shifts WHERE end_time IS NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return {"id": r[0], "start_time": r[1]} if r else None

@app.route("/api/history", methods=["GET"], endpoint="api_history_get")
def api_history_get():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id, start_time, end_time FROM shifts ORDER BY id DESC"
            ).fetchall()
        data = [{"id": r[0], "start_time": r[1], "end_time": r[2]} for r in rows]
        return jsonify(data), 200
    except Exception as e:
        # Всегда возвращаем МАССИВ, даже при ошибке
        return jsonify([]), 200
    
@app.route("/api/clear_history", methods=["POST"])
def clear_history():

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM shifts")
        conn.commit()
    return jsonify(status="cleared"), 200

@app.route("/api/download_history", methods=["GET"])
def download_history():
    rows = db_rows()  # [(id, start_time, end_time), ...]

    # собираем CSV-строку: заголовок + строки
    csv_data = "id,start_time,end_time\n"
    for row in rows:
        csv_data += f"{row[0]},{row[1]},{row[2] or ''}\n"

    # корректный HTTP-ответ с заголовками (никаких кортежей в return)
    resp = make_response(csv_data)
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = 'attachment; filename="history.csv"'
    return resp
   

@app.route("/api/stop_shift", methods=["POST"])
def stop_shift():

    """Закрывает текущую открытую смену."""
    ts = now_iso()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        open_shift = get_open_shift(conn)
        if not open_shift:
            return jsonify(error="no open shift"), 409
        c.execute("UPDATE shifts SET end_time=? WHERE id=?", (ts, open_shift["id"]))
        conn.commit()
    return jsonify(stopped_id=open_shift["id"], end_time=ts), 200

# опционально: /api/status для health-check
@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(ok=True), 200

# ---------- РОУТЫ ----------

@app.route("/api/start_shift", methods=["POST"])
def start_shift():
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            # проверяем, нет ли незакрытой смены
            open_exists = cur.execute("SELECT 1 FROM shifts WHERE end_time IS NULL LIMIT 1").fetchone()
            if open_exists:
                return jsonify(error="shift already started"), 409

            cur.execute(
                "INSERT INTO shifts (start_time, end_time) VALUES (?, ?)",
                (start_time, None)
            )
            conn.commit()
        return jsonify(status="started", start_time=start_time), 200
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route("/api/end_shift", methods=["POST"])
def end_shift():
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            # обновляем только последнюю открытую (на случай мусора)
            cur.execute("""
                UPDATE shifts
                   SET end_time = ?
                 WHERE id = (
                        SELECT id FROM shifts
                         WHERE end_time IS NULL
                         ORDER BY id DESC
                         LIMIT 1
                 )
            """, (end_time,))
            if cur.rowcount == 0:
                return jsonify(error="no open shift"), 409
            conn.commit()
        return jsonify(status="ended", end_time=end_time), 200
    except Exception as e:
        return jsonify(error=str(e)), 500

VALID_ACTIVITIES = {"drive", "rest", "other"}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_active_shift(conn):
    row = conn.execute(
        "SELECT id, start_time, activity FROM shifts WHERE end_time IS NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "start_time": row[1], "activity": row[2]}


@app.route("/api/activity/current", methods=["GET"])
def api_activity_current():
    with sqlite3.connect(DB_PATH) as conn:
        active = get_active_shift(conn)
    return jsonify(active or {}), 200


@app.route("/api/activity/start", methods=["POST"])
def api_activity_start():
    payload = request.get_json(silent=True) or {}
    activity = (payload.get("activity") or "").strip().lower()
    if activity not in VALID_ACTIVITIES:
        return jsonify(error="invalid activity", allowed=list(VALID_ACTIVITIES)), 400

    ts = now_iso()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        active = get_active_shift(conn)
        if active:
            c.execute("UPDATE shifts SET end_time=? WHERE id=?", (ts, active["id"]))
        c.execute(
            "INSERT INTO shifts(start_time, end_time, activity) VALUES(?, NULL, ?)",
            (ts, activity)
        )
        conn.commit()
        new_id = c.lastrowid

    return jsonify(id=new_id, start_time=ts, activity=activity), 201


@app.route("/api/activity/stop", methods=["POST"])
def api_activity_stop():
    ts = now_iso()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        active = get_active_shift(conn)
        if not active:
            return jsonify(error="no active shift"), 409
        c.execute("UPDATE shifts SET end_time=? WHERE id=?", (ts, active["id"]))
        conn.commit()
    return jsonify(stopped_id=active["id"], end_time=ts), 200


    
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))


