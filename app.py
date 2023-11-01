from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure random key

# Create a SQLite database connection
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

#table for messages
cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS User (
    userID INTEGER PRIMARY KEY AUTOINCREMENT,
    firstName TEXT NOT NULL,
    lastName TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashedPassword TEXT NOT NULL,
    profileImage TEXT,
    location TEXT NOT NULL,
    joinDate DATE NOT NULL,
    lastLogin DATE NOT NULL
);
''')

# Listing Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Listing (
    listingID INTEGER PRIMARY KEY AUTOINCREMENT,
    userID INTEGER,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    images TEXT,
    category TEXT NOT NULL,
    datePosted DATE NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (userID) REFERENCES User(userID)
);
''')

# Message Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Message (
    messageID INTEGER PRIMARY KEY AUTOINCREMENT,
    senderID INTEGER,
    receiverID INTEGER,
    listingID INTEGER,
    content TEXT NOT NULL,
    sendDate DATETIME NOT NULL,
    isRead BOOLEAN NOT NULL,
    FOREIGN KEY (senderID) REFERENCES User(userID),
    FOREIGN KEY (receiverID) REFERENCES User(userID),
    FOREIGN KEY (listingID) REFERENCES Listing(listingID)
);
''')

# Review Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Review (
    reviewID INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewerID INTEGER,
    reviewedUserID INTEGER,
    rating INTEGER NOT NULL,
    comment TEXT,
    datePosted DATE NOT NULL,
    FOREIGN KEY (reviewerID) REFERENCES User(userID),
    FOREIGN KEY (reviewedUserID) REFERENCES User(userID)
);
''')

# Category Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Category (
    categoryID INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);
''')

conn.commit()
conn.close()

@app.route('/registration')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    firstName = request.form['firstName']
    lastName = request.form['lastName']
    email = request.form['email']
    password = request.form['password']
    location = request.form['location']

    # Check if all required fields are filled
    if not firstName or not lastName or not email or not password or not location:
        flash('All fields are required', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Check if email already exists
    cursor.execute("SELECT * FROM User WHERE email=?", (email,))
    existing_user = cursor.fetchone()
    if existing_user:
        flash('Email already registered', 'error')
        conn.close()
        return redirect(url_for('index'))

    # Insert the new user data into the User table
    cursor.execute("INSERT INTO User (firstName, lastName, email, hashedPassword, location, joinDate, lastLogin) VALUES (?, ?, ?, ?, ?, date('now'), date('now'))", (firstName, lastName, email, password, location))

    conn.commit()
    conn.close()


    return redirect(url_for('profile'))

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('login'))

        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row  # Set row_factory to sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM User WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user is None or user['hashedPassword'] != password:  # Now you can use string keys
            flash('Invalid email or password', 'error')
        else:
            session['user_id'] = user['userID']
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
    cursor.execute("SELECT * FROM User WHERE userID=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        flash('User not found', 'error')
        return redirect(url_for('login'))

    # Extracting user information
    first_name = user['firstName']
    last_name = user['lastName']
    email = user['email']
    location = user['location']
    profile_image = user['profileImage'] if user['profileImage'] else 'default_profile_image_url'

    # Add your profile page content here
    # profile_image = user['profileImage'].split('/')[-1] if user['profileImage'] else None

    return render_template('profile.html', first_name=first_name, last_name=last_name, email=email, location=location, profile_image=profile_image)

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in to access your profile', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        # Fetch updated details from the form
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        location = request.form['location']
        profile_image = request.files['profile_image']

        # Update user details in the database
        cursor.execute("UPDATE User SET firstName=?, lastName=?, email=?, location=? WHERE userID=?", (first_name, last_name, email, location, user_id))

        # Handle profile image upload
        if profile_image:
            # Ensure the directory exists
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)

            image_path = os.path.join(UPLOAD_FOLDER, profile_image.filename)
            profile_image.save(image_path)
            # Update the image path in the database
            cursor.execute("UPDATE User SET profileImage=? WHERE userID=?", (image_path, user_id))

        conn.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))

    # Fetch current user details to pre-fill the form
    cursor.execute("SELECT * FROM User WHERE userID=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template('edit_profile.html', user=user)

@app.route('/listings', methods=['GET', 'POST'])
def listings():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        images = request.form.get('images')
        category = request.form.get('category')
        userID = session['user_id']

        cursor.execute("INSERT INTO Listing (userID, title, description, images, category, datePosted, status) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'available')", (userID, title, description, images, category))
        conn.commit()

        flash('Listing added successfully!', 'success')
        return redirect(url_for('listings'))

    cursor.execute("SELECT * FROM Listing")
    listings = cursor.fetchall()

    conn.close()
    return render_template('listings.html', listings=listings)


@app.route('/listing/<int:listing_id>', methods=['GET', 'POST'])
def view_listing(listing_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Listing WHERE listingID=?", (listing_id,))
    listing = cursor.fetchone()

    conn.close()

    if not listing:
        abort(404)  # Not found

    if request.method == 'POST':
        # Handle editing the listing if needed
        pass

    return render_template('view_listing.html', listing=listing)


@app.route('/send_message', methods=['POST'])
def send_message():
    sender_id = session.get('user_id')
    receiver_id = request.form['receiver_id']
    message = request.form['message']

    if not sender_id:
        flash('Please log in to send messages', 'error')
        return redirect(url_for('login'))

    if not receiver_id or not message:
        flash('Receiver and message are required', 'error')
        return redirect(url_for('profile'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)", (sender_id, receiver_id, message))
    conn.commit()
    conn.close()

    flash('Message sent successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/get_messages/<int:other_user_id>')
def get_messages(other_user_id):
    user_id = session.get('user_id')

    if not user_id:
        flash('Please log in to view messages', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) ORDER BY timestamp ASC", (user_id, other_user_id, other_user_id, user_id))
    messages = cursor.fetchall()
    conn.close()

    return render_template('messages.html', messages=messages)  # We'll create this template next


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)