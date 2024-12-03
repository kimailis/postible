from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import json
from datetime import datetime
import os
import hashlib
import sqlite3
from pathlib import Path

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

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=80)