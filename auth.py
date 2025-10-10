# auth.py
# Полноценная авторизация: access JWT, refresh JWT (в БД), куки, декоратор require_auth

from __future__ import annotations

import os, time, uuid, datetime as dt
from functools import wraps
import jwt
from passlib.hash import bcrypt
from flask import request, jsonify, make_response
from sqlalchemy import select, update

from db import SessionLocal           # сессии SQLAlchemy (см. db.py)
from models import User, RefreshToken # модели (см. models.py)

# ---------- настройки ----------
SECRET            = os.getenv("SECRET_KEY", "change-me")
ACCESS_TTL_MIN    = int(os.getenv("JWT_ACCESS_MIN", "20"))    # срок access-токена
REFRESH_TTL_DAYS  = int(os.getenv("JWT_REFRESH_DAYS", "14"))  # срок refresh-токена

# ---------- утилиты времени ----------
def _now_ts() -> int:
    return int(time.time())

def _utcnow() -> dt.datetime:
    # timezone-aware UTC
    return dt.datetime.now(dt.timezone.utc)

# ---------- ACCESS JWT ----------
def make_access(user: User) -> str:
    """
    Создаёт короткий access-JWT (не хранится в БД).
    """
    now  = _now_ts()
    exp  = now + ACCESS_TTL_MIN * 60
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": exp,
        "typ": "access",
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

# ---------- REFRESH JWT ----------
def make_refresh(user: User, s: SessionLocal) -> tuple[str, str, dt.datetime]:
    """
    Создаёт refresh-JWT (с уникальным jti), записывает его в БД и возвращает:
    (token, jti, expires_at).
    """
    now_dt = _utcnow()
    exp_dt = now_dt + dt.timedelta(days=REFRESH_TTL_DAYS)
    jti = uuid.uuid4().hex

    payload = {
        "sub": str(user.id),
        "typ": "refresh",
        "jti": jti,
        "iat": int(now_dt.timestamp()),
        "exp": int(exp_dt.timestamp()),
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    rt = RefreshToken(
        jti=jti,
        user_id=user.id,
        revoked=False,
        created_at=now_dt,
        expires_at=exp_dt,
    )
    s.add(rt)
    s.commit()
    return token, jti, exp_dt

def verify_refresh(token: str, s: SessionLocal) -> dict | None:
    """
    Проверяет refresh-JWT: подпись, срок, наличие и неотозван в БД.
    Возвращает payload либо None.
    """
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        if payload.get("typ") != "refresh":
            return None
        jti = payload.get("jti")
        if not jti:
            return None
        # есть ли такой jti в БД и не просрочен/не отозван
        row = s.scalar(
            select(RefreshToken).where(RefreshToken.jti == jti)
        )
        if not row or row.revoked:
            return None
        if row.expires_at <= _utcnow():
            return None
        return payload
    except jwt.PyJWTError:
        return None

def revoke_refresh_by_jti(jti: str, s: SessionLocal) -> None:
    s.execute(
        update(RefreshToken)
        .where(RefreshToken.jti == jti)
        .values(revoked=True)
    )
    s.commit()

# ---------- пользователи ----------
def register_user(username: str, password: str, role: str = "driver") -> bool:
    """
    Создаёт нового пользователя. False — если имя занято.
    """
    with SessionLocal() as s:
        exists = s.query(User).filter_by(username=username).first()
        if exists:
            return False
        user = User(
            username=username,
            password_hash=bcrypt.hash(password),
            role=role,
            is_active=True,
        )
        s.add(user)
        s.commit()
        return True

def login_user(username: str, password: str) -> User | None:
    """
    Проверяет логин/пароль. Возвращает пользователя либо None.
    """
    with SessionLocal() as s:
        user = s.query(User).filter_by(username=username).first()
        if not user:
            return None
        if not bcrypt.verify(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

# ---------- куки для refresh ----------
def set_refresh_cookie(resp, token: str) -> None:
    """
    Ставит HttpOnly cookie с refresh-токеном.
    На локалхосте Secure=False допустимо. На проде включи Secure=True.
    """
    resp.set_cookie(
        key="rt",
        value=token,
        max_age=REFRESH_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=False,         # включить True на https
        samesite="Lax",
        path="/",
    )

def clear_refresh_cookie(resp) -> None:
    resp.delete_cookie("rt", path="/")

# ---------- декоратор доступа ----------
def require_auth(*roles: str):
    """
    Декоратор: проверяет Authorization: Bearer <accessJWT>.
    Если роли указаны — проверяет, что роль пользователя в списке.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            hdr = request.headers.get("Authorization", "")
            if not hdr.startswith("Bearer "):
                return jsonify(error="no_token"), 401
            token = hdr[7:]
            try:
                payload = jwt.decode(token, SECRET, algorithms=["HS256"])
                if payload.get("typ") != "access":
                    return jsonify(error="wrong_token_type"), 401
                user_id = payload.get("sub")
                role = payload.get("role")
                if roles and role not in roles:
                    return jsonify(error="forbidden"), 403
                # прокидываем в request контекст пользователя
                request.user_id = int(user_id)
                request.user_role = role
            except jwt.ExpiredSignatureError:
                return jsonify(error="access_expired"), 401
            except jwt.PyJWTError:
                return jsonify(error="bad_access_token"), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ---------- вспомогательные вью-хэндлеры (по желанию) ----------

def handle_login():
    """
    POST /api/login {username, password} -> access, устанавливает refresh в cookie
    """
    data = request.get_json(force=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    user = login_user(username, password)
    if not user:
        return jsonify(ok=False, error="bad_credentials"), 401

    access = make_access(user)
    with SessionLocal() as s:
        refresh, jti, exp_dt = make_refresh(user, s)

    resp = make_response(jsonify(ok=True, access=access, role=user.role))
    set_refresh_cookie(resp, refresh)
    return resp

def handle_refresh():
    """
    POST /api/refresh — читает refresh из cookie, валидирует, выдаёт новый access.
    """
    rt_cookie = request.cookies.get("rt")
    if not rt_cookie:
        return jsonify(ok=False, error="no_refresh"), 401

    with SessionLocal() as s:
        payload = verify_refresh(rt_cookie, s)
        if not payload:
            return jsonify(ok=False, error="invalid_refresh"), 401

        # получаем пользователя
        user = s.get(User, int(payload["sub"]))
        if not user or not user.is_active:
            return jsonify(ok=False, error="user_inactive"), 401

        access = make_access(user)
        return jsonify(ok=True, access=access, role=user.role)

def handle_logout():
    """
    POST /api/logout — отзывает refresh (если передан в cookie) и чистит cookie.
    """
    with SessionLocal() as s:
        rt_cookie = request.cookies.get("rt")
        if rt_cookie:
            p = verify_refresh(rt_cookie, s)
            if p and "jti" in p:
                revoke_refresh_by_jti(p["jti"], s)

    resp = make_response(jsonify(ok=True))
    clear_refresh_cookie(resp)
    return resp


