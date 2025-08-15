from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_shift', methods=['POST'])
def start_shift():
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO shifts (start_time, end_time) VALUES (?, ?)', (start_time, None))
    conn.commit()
    conn.close()
    return jsonify({'status': 'started', 'start_time': start_time})

@app.route('/end_shift', methods=['POST'])
def end_shift():
    end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE shifts SET end_time = ? WHERE end_time IS NULL', (end_time,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ended', 'end_time': end_time})

@app.route('/history', methods=['GET'])
def history():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM shifts ORDER BY id DESC LIMIT 10')
    rows = c.fetchall()
    conn.close()
    return jsonify(rows)

if __name__ == '__main__':
    app.run(debug=True)
