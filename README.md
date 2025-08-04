# TrikeTime MVP

**TrikeTime** — это минимально жизнеспособный продукт (MVP) веб-приложения для дальнобойщиков.  
Приложение помогает **учитывать рабочее время**, **напоминает о паузах** и сохраняет историю смен.

---

## 🔹 Функционал MVP
- Старт и завершение смены
- Отсчёт времени работы и оставшегося времени до паузы 45 минут
- Отсчёт времени до конца смены (9 часов)
- Сохранение истории смен в локальную базу SQLite
- REST API для интеграции с фронтендом

---

## 🔹 Технологии
- **Frontend:** HTML, CSS, JavaScript  
- **Backend:** Python, Flask  
- **База данных:** SQLite  
- **Деплой:** Render (Free Tier)  
- **WSGI-сервер:** Gunicorn

---

## 🔹 Установка локально

```bash
git clone https://github.com/baraban888/TrikeTime.git
cd TrikeTime
pip install -r requirements.txt
python app.py
```