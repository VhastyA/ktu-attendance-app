import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'ktu_attendance_secret_key_2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'attendance.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Table 1: Live daily attendance sign-ins
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            index_number TEXT NOT NULL UNIQUE
        )
    ''')
    # Table 2: Pre-populated master class list
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_roster (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            index_number TEXT NOT NULL UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name')
    index_number = request.form.get('index_number')
    
    if not name or not index_number:
        return "Please fill out all fields!", 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM attendance WHERE index_number = ?', (index_number,))
    if cursor.fetchone():
        conn.close()
        return "You have already signed in for this class!", 400
        
    cursor.execute('INSERT INTO attendance (name, index_number) VALUES (?, ?)', (name, index_number))
    conn.commit()
    conn.close()
    return "Attendance recorded successfully!"

# 🔑 Shared Lecturer Login Handler
@app.route('/lecturer/login', methods=['POST'])
def lecturer_login():
    entered_password = request.form.get('password')
    next_page = request.form.get('next', 'dashboard')
    if entered_password == "KTU2026":
        session['logged_in'] = True
        return redirect(url_for(next_page))
    return render_template('login.html', error="Incorrect password!", next=next_page)

# 📊 1. LIVE ATTENDANCE ROSTER
@app.route('/lecturer/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return render_template('login.html', next='dashboard')
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM attendance ORDER BY name ASC')
    students = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', students=students)

# 📂 2. MASTER CLASS REGISTRY SETUP (Your Drag & Drop Page)
@app.route('/lecturer/roster', methods=['GET', 'POST'])
def roster():
    if not session.get('logged_in'):
        return render_template('login.html', next='roster')
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        index_number = request.form.get('index_number')
        try:
            cursor.execute('INSERT INTO master_roster (name, index_number) VALUES (?, ?)', (name, index_number))
            conn.commit()
        except sqlite3.IntegrityError:
            pass # Ignore duplicates in setup
            
    cursor.execute('SELECT * FROM master_roster ORDER BY name ASC')
    students = cursor.fetchall()
    conn.close()
    return render_template('view.html', students=students)

@app.route('/lecturer/clear', methods=['POST'])
def clear_attendance():
    if not session.get('logged_in'):
        return "Unauthorized", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM attendance')
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/lecturer/clear-roster', methods=['POST'])
def clear_roster():
    if not session.get('logged_in'):
        return "Unauthorized", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM master_roster')
    conn.commit()
    conn.close()
    return redirect(url_for('roster'))

@app.route('/lecturer/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
