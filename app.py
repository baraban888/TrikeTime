from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import os
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SEKRET_KEY'] = os.environ.get('SEKRET_KEY','fallback_secret_key')
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
@app.route('/clear_history', methods=['POST'])
def clear_history():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM shifts')
    conn.commit()
    conn.close()
    return jsonify({'status': 'cleared'})

@app.route('/download_history', methods=['GET'])
def download_history():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM shifts ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()

    csv_data = "id,start_time,end_time\n"
    for row in rows:
        csv_data += f"{row[0]},{row[1]},{row[2]}\n"

    return csv_data, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="history.csv"'
    }
import os
if __name__ == '__main__':
 port=int (os.environ.get('PORT',5000))
app.run(host='0.0.0.0.', port=port, debug=False)

             