import flask
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure random key

# Create a SQLite database connection
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Create a table for user registration
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL
                )''')
conn.commit()
conn.close()

@app.route('/registration')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    if not username or not password:
        flash('Username and password are required', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

    flash('Registration successful', 'success')
    return redirect(url_for('index'))

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('login'))

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user is None or user[2] != password:
            flash('Invalid username or password', 'error')
        else:
            session['user_id'] = user[0]
            flash('Login successful', 'success')
            return redirect(url_for('profile'))

    return render_template('login.html')

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in to access your profile', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    user_name = user['username']


    # Add your profile page content here
    return render_template('profile.html', user_name = user_name, user_id = user_id)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
