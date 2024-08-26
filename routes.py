from flask import Blueprint, request, jsonify, redirect, url_for, session, render_template
from app_factory import db
from models import User, Friendship
import bcrypt  # Ensure bcrypt is imported

main_routes = Blueprint('main_routes', __name__)

@main_routes.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Check if the username or email already exists
        if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
            return jsonify({'message': 'Username or email already exists'}), 400

        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id  # Log the user in after successful signup
        return jsonify({'message': 'Signup successful'}), 201

    return render_template('signup.html')  # Use your existing signup.html

@main_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            session['user_id'] = user.id  # Log the user in
            return jsonify({'message': 'Login successful'}), 200
        else:
            return jsonify({'message': 'Invalid email or password'}), 401

    return render_template('login.html')  # Use your existing login.html


@main_routes.route('/homepage')
def homepage():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('main_routes.login'))

    user = User.query.get(user_id)
    friends = Friendship.query.filter_by(user_id=user.id).all()
    friend_list = [{'username': User.query.get(f.friend_id).username, 'email': User.query.get(f.friend_id).email} for f in friends]

    return render_template('home.html', user=user, friends=friend_list)

@main_routes.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main_routes.login'))

@main_routes.route('/add_friend', methods=['POST'])
def add_friend():
    data = request.get_json()
    friend_username = data.get('friend_username')

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'You need to be logged in to add friends'}), 401

    user = User.query.get(user_id)
    friend = User.query.filter_by(username=friend_username).first()

    if not friend:
        return jsonify({'message': 'User not found'}), 404

    # Check if already friends
    existing_friendship = Friendship.query.filter_by(user_id=user.id, friend_id=friend.id).first()
    if existing_friendship:
        return jsonify({'message': 'You are already friends with this user'}), 400

    # Add friend
    new_friendship = Friendship(user_id=user.id, friend_id=friend.id, status='accepted')
    db.session.add(new_friendship)
    db.session.commit()

    return jsonify({'message': 'Friend added successfully'}), 200
