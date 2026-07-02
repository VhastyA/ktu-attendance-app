import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)

# Secret key required to use sessions (login states) securely
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            index_number TEXT NOT NULL UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 1. Student Sign-In Page (Homepage)
@app.route('/')
def index():
    return render_template('index.html')

# 2. Student Form Submission Route (With Duplicate Prevention)
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name')
    index_number = request.form.get('index_number')
    
    if not name or not index_number:
        return "Please fill out all fields!", 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 🛡️ Guard Check: Look if this Index Number has already signed in
    cursor.execute('SELECT * FROM attendance WHERE index_number = ?', (index_number,))
    existing_student = cursor.fetchone()
    
    if existing_student:
        conn.close()
        return "You have already signed in for this class!", 400
        
    cursor.execute('INSERT INTO attendance (name, index_number) VALUES (?, ?)', (name, index_number))
    conn.commit()
    conn.close()
    
    return "Attendance submitted successfully! Thank you."

# 3. Lecturer Dashboard & Login Logic
@app.route('/lecturer/dashboard', methods=['GET', 'POST'])
def dashboard():
    # If the lecturer is submitting the password form
    if request.method == 'POST':
        entered_password = request.form.get('password')
        if entered_password == "KTU2026":  # 🔑 Your secret password
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('dashboard.html', error="Incorrect password! Please try again.")

    # Check if the lecturer is already logged in
    if not session.get('logged_in'):
        # If not logged in, render the dashboard template but tell it to show the login screen
        return render_template('dashboard.html', show_login=True)

    # If logged in, fetch the roster data
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM attendance ORDER BY name ASC')
    students = cursor.fetchall()
    conn.close()
    
    return render_template('dashboard.html', students=students, show_login=False)

# 4. Lecturer Logout
@app.route('/lecturer/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('dashboard'))

# 5. Clear Attendance Session
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

if __name__ == '__main__':
    app.run(debug=True)
