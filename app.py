import os
import sqlite3
import random
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, Response

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_flash_messages'

# This automatically finds your project folder and forces the database file to be created there
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'attendance.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Attendance logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            index_number TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # 2. Official Class Roster table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_roster (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            index_number TEXT NOT NULL UNIQUE
        )
    ''')
    
    # 3. Session control table (Stores active PIN)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_control (
            id INTEGER PRIMARY KEY,
            is_active INTEGER DEFAULT 0,
            current_pin TEXT DEFAULT ''
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM session_control")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO session_control (id, is_active, current_pin) VALUES (1, 0, '')")
        conn.commit()
        
    conn.close()

def get_session_status():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT is_active, current_pin FROM session_control WHERE id = 1")
    session = cursor.fetchone()
    conn.close()
    return {"is_active": session[0], "current_pin": session[1]}

# 1. Student Sign-In Page
@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT student_name, index_number FROM student_roster")
    roster = cursor.fetchall()
    conn.close()
    
    session = get_session_status()
    return render_template('index.html', roster=roster, session=session)

# 2. Handle Student Attendance Submission
@app.route('/submit', methods=['POST'])
def submit_attendance():
    name = request.form.get('name').strip()
    index_num = request.form.get('index_number').strip()
    student_pin = request.form.get('session_pin').strip()
    
    session = get_session_status()
    
    if not session['is_active']:
        flash("Error: Attendance tracking is closed for this lecture session!", "error")
        return redirect(url_for('index'))
        
    if student_pin != session['current_pin']:
        flash("Error: Invalid Session PIN! Please check the projector board.", "error")
        return redirect(url_for('index'))
        
    if not name or not index_num:
        flash("Please fill in all fields!", "error")
        return redirect(url_for('index'))
        
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO attendance (student_name, index_number, timestamp) VALUES (?, ?, ?)", 
                   (name, index_num, current_time))
    conn.commit()
    conn.close()
    
    flash(f"Success! Attendance logged for {name}.", "success")
    return redirect(url_for('index'))

# 3. Lecturer Dashboard
@app.route('/lecturer/dashboard')
def view_attendance():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT student_name, index_number, timestamp FROM attendance ORDER BY timestamp DESC")
    records = cursor.fetchall()
    conn.close()
    
    session = get_session_status()
    return render_template('view.html', records=records, session=session)

# 4. Generate/Update Session PIN
@app.route('/lecturer/session', methods=['POST'])
def update_session():
    action = request.form.get('action')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if action == 'start':
        new_pin = str(random.randint(1000, 9999))
        cursor.execute("UPDATE session_control SET is_active = 1, current_pin = ? WHERE id = 1", (new_pin,))
        flash(f"Attendance session started! Active PIN: {new_pin}", "success")
    elif action == 'stop':
        cursor.execute("UPDATE session_control SET is_active = 0, current_pin = '' WHERE id = 1")
        flash("Attendance session closed successfully.", "success")
        
    conn.commit()
    conn.close()
    return redirect(url_for('view_attendance'))

# 5. Lecturer Roster Management
@app.route('/lecturer/roster', methods=['GET', 'POST'])
def manage_roster():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('student_name').strip()
        index_num = request.form.get('index_number').strip()
        
        if name and index_num:
            try:
                cursor.execute("INSERT INTO student_roster (student_name, index_number) VALUES (?, ?)", (name, index_num))
                conn.commit()
                flash(f"Added {name} to the class roster successfully!", "success")
            except sqlite3.IntegrityError:
                flash(f"Error: A student with Index Number {index_num} already exists!", "error")
                
    cursor.execute("SELECT student_name, index_number FROM student_roster ORDER BY student_name ASC")
    roster = cursor.fetchall()
    conn.close()
    return render_template('roster.html', roster=roster)

# 6. Export Logs to Excel (CSV)
@app.route('/lecturer/export')
def export_attendance():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT student_name, index_number, timestamp FROM attendance ORDER BY timestamp DESC")
    records = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Index Number', 'Time Signed'])
    for row in records:
        writer.writerow(row)
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=attendance_report.csv"}
    )

# 7. Clear All Logs
@app.route('/lecturer/clear', methods=['POST'])
def clear_attendance():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='attendance'")
    conn.commit()
    conn.close()
    flash("Attendance log cleared successfully!", "success")
    return redirect(url_for('view_attendance'))
    
init_db()
if __name__ == '__main__':
    app.run(debug=True)
