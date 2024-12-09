from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import json
from datetime import datetime
import os
import hashlib
import sqlite3
from pathlib import Path


import random
import string
from time import sleep
import requests
from html import unescape

from threading import Thread
import time


app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Ensure the db directory exists
Path("db").mkdir(exist_ok=True)

def init_db():
    conn = sqlite3.connect('db/users.db')
    c = conn.cursor()
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Posts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # Likes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('app.html', username=session.get('username'))
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        conn = sqlite3.connect('db/users.db')
        c = conn.cursor()
        
        # Check if username already exists
        c.execute('SELECT username FROM users WHERE username = ?', (username,))
        if c.fetchone():
            return jsonify({'error': 'Username already exists'}), 409

        # Hash password and insert new user
        hashed_password = hash_password(password)
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                 (username, hashed_password))
        conn.commit()
        
        return jsonify({'message': 'User registered successfully'}), 201

    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@app.route('/posts/liked')
def get_liked_posts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = sqlite3.connect('db/users.db')
        c = conn.cursor()
        
        # Get only liked posts for the current user
        c.execute('''
            SELECT 
                p.id,
                p.content,
                p.created_at,
                u.username,
                u.id as author_id,
                COUNT(l2.user_id) as likes,
                1 as liked
            FROM posts p
            JOIN users u ON p.user_id = u.id
            JOIN likes l1 ON p.id = l1.post_id AND l1.user_id = ?
            LEFT JOIN likes l2 ON p.id = l2.post_id
            GROUP BY p.id
            ORDER BY p.created_at DESC
        ''', (session['user_id'],))
        
        posts = []
        for row in c.fetchall():
            posts.append({
                'id': row[0],
                'content': row[1],
                'created_at': row[2],
                'username': row[3],
                'isAuthor': row[4] == session['user_id'],
                'likes': row[5],
                'liked': bool(row[6])
            })
        
        return jsonify(posts)

    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        conn = sqlite3.connect('db/users.db')
        c = conn.cursor()
        
        # Get user from database
        c.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        
        if not user or user[2] != hash_password(password):
            return jsonify({'error': 'Invalid username or password'}), 401

        # Store user info in session
        session['user_id'] = user[0]
        session['username'] = user[1]

        return jsonify({'message': 'Login successful', 'username': username}), 200

    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/posts')
def get_posts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = sqlite3.connect('db/users.db')
        c = conn.cursor()
        
        # Get all posts with user information and like counts
        c.execute('''
            SELECT 
                p.id,
                p.content,
                p.created_at,
                u.username,
                u.id as author_id,
                COUNT(l.user_id) as likes,
                MAX(CASE WHEN l.user_id = ? THEN 1 ELSE 0 END) as liked
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN likes l ON p.id = l.post_id
            GROUP BY p.id
            ORDER BY p.created_at DESC
        ''', (session['user_id'],))
        
        posts = []
        for row in c.fetchall():
            posts.append({
                'id': row[0],
                'content': row[1],
                'created_at': row[2],
                'username': row[3],
                'isAuthor': row[4] == session['user_id'],
                'likes': row[5],
                'liked': bool(row[6])
            })
        
        return jsonify(posts)

    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@app.route('/posts', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    content = data.get('content')

    if not content:
        return jsonify({'error': 'Content is required'}), 400

    try:
        conn = sqlite3.connect('db/users.db')
        c = conn.cursor()
        
        # Insert new post
        c.execute('''
            INSERT INTO posts (user_id, content)
            VALUES (?, ?)
        ''', (session['user_id'], content))
        
        post_id = c.lastrowid
        conn.commit()

        # Get the created post with user information
        c.execute('''
            SELECT 
                p.id,
                p.content,
                p.created_at,
                u.username,
                u.id as author_id,
                0 as likes,
                0 as liked
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        ''', (post_id,))
        
        post = c.fetchone()
        new_post = {
            'id': post[0],
            'content': post[1],
            'created_at': post[2],
            'username': post[3],
            'isAuthor': post[4] == session['user_id'],
            'likes': post[5],
            'liked': bool(post[6])
        }
        
        # Emit the new post to all connected clients
        socketio.emit('new_post', new_post)
        
        return jsonify(new_post), 201

    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@app.route('/posts/my')
def get_my_posts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = sqlite3.connect('db/users.db')
        c = conn.cursor()
        
        # Get only posts created by the current user
        c.execute('''
            SELECT 
                p.id,
                p.content,
                p.created_at,
                u.username,
                u.id as author_id,
                COUNT(l.user_id) as likes,
                MAX(CASE WHEN l.user_id = ? THEN 1 ELSE 0 END) as liked
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN likes l ON p.id = l.post_id
            WHERE p.user_id = ?
            GROUP BY p.id
            ORDER BY p.created_at DESC
        ''', (session['user_id'], session['user_id']))
        
        posts = []
        for row in c.fetchall():
            posts.append({
                'id': row[0],
                'content': row[1],
                'created_at': row[2],
                'username': row[3],
                'isAuthor': True,  # Always true since these are user's own posts
                'likes': row[5],
                'liked': bool(row[6])
            })
        
        return jsonify(posts)

    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()

@app.route('/posts/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = sqlite3.connect('db/users.db')
        c = conn.cursor()

        # Check if the post exists and if the user is not the author
        c.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
        post = c.fetchone()
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        if post[0] == session['user_id']:
            return jsonify({'error': 'Cannot like your own post'}), 400

        # Check if the user has already liked the post
        c.execute('SELECT * FROM likes WHERE user_id = ? AND post_id = ?',
                 (session['user_id'], post_id))
        existing_like = c.fetchone()

        if existing_like:
            # Unlike the post
            c.execute('DELETE FROM likes WHERE user_id = ? AND post_id = ?',
                     (session['user_id'], post_id))
            action = 'unliked'
        else:
            # Like the post
            c.execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)',
                     (session['user_id'], post_id))
            action = 'liked'

        conn.commit()

        # Get updated like count
        c.execute('''
            SELECT COUNT(*) as likes
            FROM likes
            WHERE post_id = ?
        ''', (post_id,))
        
        like_count = c.fetchone()[0]

        # Emit like update to all clients
        socketio.emit('like_update', {
            'post_id': post_id,
            'likes': like_count,
            'action': action,
            'user_id': session['user_id']
        })

        return jsonify({
            'message': f'Post {action}',
            'likes': like_count
        }), 200

    except sqlite3.Error as e:
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        conn.close()


def get_random_post_content():
    """Fetch random content from various APIs for posts"""
    # List of APIs to try
    apis = [
        
        # Random quotes
        {
            'url': 'https://api.quotable.io/random',
            'parser': lambda r: f'"{r.json()["content"]}" - {r.json()["author"]}'
        },
        # Random facts
        {
            'url': 'https://uselessfacts.jsph.pl/random.json?language=en',
            'parser': lambda r: r.json()['text']
        },
         # Tech facts
        {
            'url': 'http://numbersapi.com/random/trivia?json=true&type=cs',
            'parser': lambda r: r.json()['text']
        },
        
        {
            'url': 'https://www.boredapi.com/api/activity',
            'parser': lambda r: f"Try this activity: {r.json()['activity']}"
        },
        {
            'url': 'https://api.quotable.io/random',
            'parser': lambda r: f'"{r.json()["content"]}" - {r.json()["author"]}'
        },
        {
            'url': 'https://v2.jokeapi.dev/joke/Any?type=single',
            'parser': lambda r: f'"{r.json()["joke"]}"'
        },
        {
            'url': 'https://futurism.com/api/v1/articles',
            'parser': lambda r: f"{r.json()['articles'][0]['title']}<br>URL : {r.json()['articles'][0]['url']}"
        },
        
        {
            'url': 'https://techcrunch.com/wp-json/wp/v2/posts?per_page=1',
            'parser': lambda r: f"{r.json()[0]['title']['rendered']} <br>URL : {r.json()[0]['link']}"

        }


    ]

    # Try each API until we get a successful response
    for api in random.sample(apis, len(apis)):
        try:
            response = requests.get(api['url'], timeout=5)
            if response.status_code == 200:
                content = api['parser'](response)
                # Ensure content isn't too long and clean it up
                content = unescape(content)[:400].strip()
                return content
        except Exception as e:
            continue

    # Fallback content if all APIs fail
    return "Just thinking about how amazing technology is! 💭"

def create_seed_posts():
    """Create random posts for seed users using web content"""
    try:
        conn = sqlite3.connect('db/users.db')
        c = conn.cursor()
        
        # Get all users
        c.execute('SELECT id, username FROM users')
        users = c.fetchall()
        
        if not users:
            print("No users found in database")
            return
        
        # Create 10 rounds of posts
        for round_num in range(10):
            # Select random subset of users for this round
            posting_users = random.sample(
                users,
                random.randint(1, min(3, len(users)))
            )
            
            for user in posting_users:
                # Get content from web APIs
                post_content = get_random_post_content()
                c.execute(
                    'INSERT INTO posts (user_id, content) VALUES (?, ?)',
                    (user[0], post_content)
                )
                
                print(f"Created post for {user[1]}: {post_content[:50]}...")
                
            conn.commit()
            sleep(1)  # Slightly longer delay to respect API rate limits
            
        print("Finished creating seed posts")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()



def generate_password(length=6):
    """Generate a random password of specified length"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for _ in range(length))

def create_seed_users():
    """Create 10 predefined users if they don't exist"""
    usernames = [
        'josh01', 'almondbabe', 'danaflow', 'old_zealand', 
        'legumeister', 'no-pro', 'zmey', 'freund', 'samara', 'despasito'
    ]
    
    created_users = []
    
    try:
        conn = sqlite3.connect('db/users.db')
        c = conn.cursor()
        
        for username in usernames:
            # Check if user exists
            c.execute('SELECT username FROM users WHERE username = ?', (username,))
            if not c.fetchone():
                password = generate_password()
                hashed_password = hash_password(password)
                
                c.execute(
                    'INSERT INTO users (username, password) VALUES (?, ?)',
                    (username, hashed_password)
                )
                
                created_users.append({
                    'username': username,
                    'password': password  # Store unhashed for testing purposes
                })
        
        conn.commit()
        print(f"Created {len(created_users)} new seed users")
        return created_users
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()

def initialize_with_seed_data():
    created_users = create_seed_users()
    if created_users:
        print("Created the following seed users:")
        for user in created_users:
            print(f"Username: {user['username']}, Password: {user['password']}")
    create_seed_posts()


def auto_post_content():
    """
    Automatically creates posts every 5 minutes using random seed users.
    Runs in a separate thread while the server is running.
    """
    # Copy the list of usernames to avoid modifying the original
    usernames = [
        'josh01', 'almondbabe', 'danaflow', 'old_zealand', 
        'legumeister', 'no-pro', 'zmey', 'freund', 'samara', 'despasito'
    ]
    
    while True:
        try:
            # Connect to database
            conn = sqlite3.connect('db/users.db')
            c = conn.cursor()
            
            # Get a random username from the list
            random_username = random.choice(usernames)
            
            # Get the user_id for the random username
            c.execute('SELECT id FROM users WHERE username = ?', (random_username,))
            user = c.fetchone()
            
            if user:
                # Get random content for the post
                content = get_random_post_content()
                
                # Create the post
                c.execute(
                    'INSERT INTO posts (user_id, content) VALUES (?, ?)',
                    (user[0], content)
                )
                
                # Get the created post details for the socket emission
                post_id = c.lastrowid
                c.execute('''
                    SELECT 
                        p.id,
                        p.content,
                        p.created_at,
                        u.username,
                        u.id as author_id,
                        0 as likes,
                        0 as liked
                    FROM posts p
                    JOIN users u ON p.user_id = u.id
                    WHERE p.id = ?
                ''', (post_id,))
                
                post = c.fetchone()
                new_post = {
                    'id': post[0],
                    'content': post[1],
                    'created_at': post[2],
                    'username': post[3],
                    'isAuthor': False,
                    'likes': post[5],
                    'liked': bool(post[6])
                }
                
                conn.commit()
                
                # Emit the new post to all connected clients
                socketio.emit('new_post', new_post)
                
                print(f"Auto-posted as {random_username}: {content[:50]}...")
                
        except Exception as e:
            print(f"Error in auto posting: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
        
        # Wait for 5 minutes before the next post
        time.sleep(120)

def start_auto_posting():
    """Start the auto-posting thread"""
    auto_post_thread = Thread(target=auto_post_content, daemon=True)
    auto_post_thread.start()

if __name__ == '__main__':
    init_db()
    initialize_with_seed_data()
    start_auto_posting()
    socketio.run(app, debug=True, host='0.0.0.0', port=80)