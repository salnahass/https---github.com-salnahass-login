from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import sqlite3
import os
import re



# UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure random key
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
# Define the upload folder path
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Ensure the UPLOAD_FOLDER exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
# Allowed extensions for file upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure the UPLOAD_FOLDER directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

def validate_title(title):
    title = title.strip()  # Trim spaces from start and end
    
    if not title:
        return False, "Title must not be empty."
    if not (10 <= len(title) <= 100):
        return False, "Title must be between 10 and 100 characters in length."
    if re.search(r'[<>&%#]', title):
        return False, "Title cannot contain special characters."
    
    return True, "Title is valid."

def validate_description(description):
    description = description.strip()  # Trim spaces from start and end
    
    if not description:
        return False, "Description must not be empty."
    if len(description) < 20:
        return False, "Description must be at least 20 characters in length."
    if len(description) > 2000:
        return False, "Description must not exceed 2000 characters."
    if re.search(r'[<>&%#]', description):
        return False, "Description cannot contain special characters."
    
    return True, "Description is valid."



def validate_image_url(url):
    url = url.strip()  # Trim spaces from start and end
    
    # Basic URL validation using regex
    pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    if url and not pattern.match(url):
        return False, "Invalid URL format."
    
    # Additional checks can be added to ensure URL doesn't lead to malicious websites
    
    return True, "URL is valid."


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/registration')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        email = request.form['email']
        password = request.form['password']
        location = request.form['location']
        profile_image = request.files['profileImage']

        # Check if all required fields are filled
        if not firstName or not lastName or not email or not password or not location:
            flash('All fields are required', 'error')
            return redirect(url_for('register'))

        # Check if the file is one of the allowed types/extensions
        if profile_image and allowed_file(profile_image.filename):
            filename = secure_filename(profile_image.filename)
            profile_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            profile_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        else:
            flash('Invalid image format', 'error')
            return redirect(url_for('register'))

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
    cursor.execute("INSERT INTO User (firstName, lastName, email, hashedPassword, profileImage, location, joinDate, lastLogin) VALUES (?, ?, ?, ?, ?, ?, date('now'), date('now'))", (firstName, lastName, email, password, profile_image_path, location))
    conn.commit()
    

    # Fetch the userID of the newly registered user
    cursor.execute("SELECT userID FROM User WHERE email=?", (email,))
    user = cursor.fetchone()

    # Log the user in by setting the userID in the session
    session['user_id'] = user[0]

    conn.close()

    flash('Registered successfully. You are now logged in.', 'success')
    return redirect(url_for('profile'))  # Redirect to profile or another desired page


@app.route('/')
def landing():
    return render_template('landing.html')
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
    # retrieve user id from previous page
    userid = request.args.get('user_id')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM User WHERE userID=?", (user_id,))
    user = cursor.fetchone()

    # Fetch the listings created by the logged-in user
    cursor.execute("SELECT * FROM Listing WHERE userID=?", (userid,))
    user_listings = cursor.fetchall()

    # conn.close()

    if user is None:
        flash('User not found', 'error')
        return redirect(url_for('login'))

    # Extracting user information
    first_name = user['firstName']
    last_name = user['lastName']
    email = user['email']
    location = user['location']
    profile_image = user['profileImage'] if user['profileImage'] else 'uploads/defaultpfp.jpg'

# Fetch the reviews for the user
    cursor.execute("SELECT * FROM Review WHERE reviewedUserID=?", (user_id,))
    user_reviews = cursor.fetchall()

    return render_template('profile.html', first_name=first_name, last_name=last_name, email=email, location=location, profile_image=profile_image, user_listings=user_listings, user_reviews=user_reviews)

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
        location = request.form['location']
        profile_image = request.files['profile_image']

        # Update user details in the database
        cursor.execute("UPDATE User SET firstName=?, lastName=?, location=? WHERE userID=?", (first_name, last_name, location, user_id))

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

@app.route('/submit_review')
def submit_review_form():
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to submit a review.', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT userID, firstName, lastName FROM User WHERE userID != ?", (session['user_id'],))
    users = cursor.fetchall()
    conn.close()
    for u in users:
        print (u)
    return render_template('submit_review.html', users=users)

@app.route('/submit_review', methods=['POST'])
def submit_review():
    reviewer_id = session.get('user_id')
    reviewed_user_id = request.form.get('reviewed_user_id')
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    if not reviewer_id:
        flash('You must be logged in to submit a review.', 'error')
        return redirect(url_for('login'))

    if reviewer_id == reviewed_user_id:
        flash('You cannot review yourself.', 'error')
        return redirect(url_for('user_reviews', user_id=reviewed_user_id))

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            flash('Rating must be between 1 and 5.', 'error')
            return redirect(url_for('user_reviews', user_id=reviewed_user_id))
    except ValueError:
        flash('Invalid rating.', 'error')
        return redirect(url_for('user_reviews', user_id=reviewed_user_id))

    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Review (reviewerID, reviewedUserID, rating, comment, datePosted)
            VALUES (?, ?, ?, ?, date('now'))
        ''', (reviewer_id, reviewed_user_id, rating, comment))
        conn.commit()
    except sqlite3.IntegrityError as e:
        flash('An error occurred while submitting the review: ' + str(e), 'error')
        return redirect(url_for('user_reviews', user_id=reviewed_user_id))
    finally:
        conn.close()

    flash('Your review has been submitted.', 'success')
    return redirect(url_for('user_reviews', user_id=reviewed_user_id))


@app.route('/user_reviews/<int:user_id>')
def user_reviews(user_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*, u.firstName, u.lastName FROM Review r
        JOIN User u ON r.reviewerID = u.userID
        WHERE r.reviewedUserID = ?
    """, (user_id,))

    reviews = cursor.fetchall()
    conn.close()

    return render_template('user_reviews.html', reviews=reviews)

@app.route('/users')
def users():
    # Ensure the user is logged in before they can see the list of users
    if 'user_id' not in session:
        flash('Please log in to view registered users', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Select all users except the one who's currently logged in
    current_user_id = session['user_id']
    print (current_user_id)
    cursor.execute("SELECT * FROM User WHERE userID != ?", (current_user_id,))
    registered_users = cursor.fetchall()
    conn.close()
    print (registered_users)
    return render_template('users.html', users=registered_users)

@app.route('/user_profile/<int:user_id>')
def user_profile(user_id):

    # userid = request.args.get('user_id')

    # Create a database connection
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # This allows us to access the columns by name
    cursor = conn.cursor()

    # Fetch the user's profile using the user_id
    cursor.execute("SELECT * FROM User WHERE userID = ?", (user_id,))
    user = cursor.fetchone()
    # Close the database connection
    # conn.close()

    # Check if the user was found
    if user is None:
        # User was not found, redirect or show an error
        flash('User not found', 'error')
        return redirect(url_for('index'))  # Redirect to the home page or a 404 page

    # Fetch the reviews for the user
    cursor.execute("SELECT * FROM Review WHERE reviewedUserID = ?", (user_id,))
    user_reviews = cursor.fetchall()
    print (user_id)
    print (user_reviews)


    # If the user was found, render the user_profile.html template with the user data
    return render_template('user_profile.html', profile=user, user_reviews = user_reviews)

# Make sure to create a user_profile.html template that expects a 'profile' variable


@app.route('/listings', methods=['GET'])
def listings():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Listing")
    listings = cursor.fetchall()
    conn.close()
    return render_template('listings.html', listings=listings)


@app.route('/listing/<int:listing_id>', methods=['GET', 'POST'])
def view_listing(listing_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Set row factory
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Listing WHERE listingID=?", (listing_id,))
    listing = cursor.fetchone()

    if not listing:
        abort(404)  # Not found

    # Fetch the user details of the person who created the listing
    cursor.execute("SELECT * FROM User WHERE userID=?", (listing['userID'],))
    user = cursor.fetchone()

    conn.close()

    if request.method == 'POST':
        # Handle sending a message to the listing creator
        sender_id = session['user_id']
        receiver_id = user['userID']
        content = request.form.get('message_content')
        
        # Insert the message into the Message table
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Message (senderID, receiverID, listingID, content, sendDate, isRead) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 0)", (sender_id, receiver_id, listing_id, content))
        conn.commit()
        conn.close()

        flash('Message sent successfully!', 'success')
        return redirect(url_for('view_listing', listing_id=listing_id))

    return render_template('view_listing.html', listing=listing, user=user)

@app.route('/create_listing')
def create_listing():
    return render_template('create_listing.html')

@app.route('/add_listing', methods=['GET', 'POST'])
def add_listing():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        userID = session['user_id']
        image = request.files['image']

        # Validate and save the image if it exists
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_url = url_for('uploaded_file', filename=filename)
        else:
            image_url = ''  # or a default image URL if you prefer

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Listing (userID, title, description, images, category, datePosted, status) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'available')", (userID, title, description, image_url, category))
        conn.commit()
        conn.close()

        return redirect(url_for('listings'))

    return render_template('add_listing.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}



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
