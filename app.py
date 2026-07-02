import os
import sqlite3
import random
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'ktu_attendance_secret_key_2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'attendance.db')

# Global state tracker for the active OTP code (None means session is locked)
CURRENT_OTP = None

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            index_number TEXT NOT NULL UNIQUE
        )
    ''')
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
    # Send whether the session is open or locked to the student page
    return render_template('index.html', session_active=(CURRENT_OTP is not None))

# Student Form Submission Check
@app.route('/submit', methods=['POST'])
def submit():
    global CURRENT_OTP
    
    # 1. Check if attendance is completely locked down
    if CURRENT_OTP is None:
        return "Attendance session is currently locked by the lecturer!", 400
        
    name = request.form.get('name')
    index_number = request.form.get('index_number')
    student_otp = request.form.get('otp')
    
    if not name or not index_number or not student_otp:
        return "Please fill out all fields including the Access Code!", 400
        
    # 2. Validate OTP
    if student_otp.strip() != str(CURRENT_OTP):
        return "Invalid Access Code! Please check the board.", 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 3. Check for duplicates
    cursor.execute('SELECT * FROM attendance WHERE index_number = ?', (index_number,))
    if cursor.fetchone():
        conn.close()
        return "You have already signed in for this class!", 400
        
    cursor.execute('INSERT INTO attendance (name, index_number) VALUES (?, ?)', (name, index_number))
    conn.commit()
    conn.close()
    return "Attendance recorded successfully!"

# Manual add to master roster registry
@app.route('/submit-master', methods=['POST'])
def submit_master():
    if not session.get('logged_in'):
        return "Unauthorized", 403
    name = request.form.get('name')
    index_number = request.form.get('index_number')
    
    if not name or not index_number:
        return "Missing fields", 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO master_roster (name, index_number) VALUES (?, ?)', (name, index_number))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()
    return redirect(url_for('roster'))

# 🔑 Lecturer Security Controls
@app.route('/lecturer/generate-otp', methods=['POST'])
def generate_otp():
    global CURRENT_OTP
    if not session.get('logged_in'):
        return "Unauthorized", 403
    CURRENT_OTP = random.randint(1000, 9999) # Generates a random 4-digit token
    return redirect(url_for('dashboard'))

@app.route('/lecturer/lock-session', methods=['POST'])
def lock_session():
    global CURRENT_OTP
    if not session.get('logged_in'):
        return "Unauthorized", 403
    CURRENT_OTP = None # Clears the code, locking out submissions
    return redirect(url_for('dashboard'))

@app.route('/lecturer/login', methods=['GET', 'POST'])
def lecturer_login():
    if request.method == 'POST':
        entered_password = request.form.get('password')
        next_page = request.form.get('next', 'dashboard')
        if entered_password == "KTU2026":
            session['logged_in'] = True
            return redirect(url_for(next_page))
        return render_template('login.html', error="Incorrect password!", next=next_page)
    return render_template('login.html', next=request.args.get('next', 'dashboard'))

@app.route('/lecturer/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('lecturer_login', next='dashboard'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM attendance ORDER BY name ASC')
    students = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', students=students, current_otp=CURRENT_OTP)

@app.route('/lecturer/roster')
def roster():
    if not session.get('logged_in'):
        return redirect(url_for('lecturer_login', next='roster'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
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
