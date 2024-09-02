from flask import Blueprint, request, jsonify, redirect, url_for, session, render_template
from app_factory import db
from models import User, Friendship
import bcrypt
import os
from werkzeug.utils import secure_filename
from datetime import datetime

main_routes = Blueprint('main_routes', __name__)

@main_routes.route('/', methods=['GET'])
def startscreen():
    return redirect(url_for('main_routes.homepage'))


@main_routes.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({'message': 'Missing required fields'}), 400

        if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
            return jsonify({'message': 'Username or email already exists'}), 400

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
    
        return redirect(url_for('main_routes.homepage'))
        

    return render_template('signup.html')

@main_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Missing required fields'}), 400

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            user.is_online = True
            user.last_active = datetime.utcnow()
            db.session.commit()
            
            
            session['user_id'] = user.id
            return jsonify({'message': 'Login successful'}), 200
        return jsonify({'message': 'Invalid email or password'}), 401

    return render_template('login.html')
@main_routes.route('/homepage')
def homepage():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('main_routes.login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('main_routes.login'))

    friends = Friendship.query.filter(
        (Friendship.user_id == user_id) | (Friendship.friend_id == user_id),
        Friendship.status == 'accepted'
    ).all()

    friend_list = []
    for f in friends:
        friend_id = f.friend_id if f.user_id == user_id else f.user_id
        friend = User.query.get(friend_id)
        friend_list.append({
            'username': friend.username,
            'id': friend.id,
            'profile_picture': friend.profile_picture,
            'is_online': friend.is_online
        })

    return render_template('home.html', current_user=user, friends=friend_list)
@main_routes.route('/settings', methods=['GET', 'POST'])
def settings():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('main_routes.login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('main_routes.login'))

    if request.method == 'POST':
        data = request.form

        # Handle username change
        new_username = data.get('username')
        if new_username and new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                return jsonify({'message': 'Username already exists'}), 400
            user.username = new_username
            db.session.commit()

        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                user.profile_picture = filename
                db.session.commit()

        return redirect(url_for('main_routes.settings'))

    return render_template('settings.html', user=user)

# Delete Account Route
@main_routes.route('/delete_account', methods=['POST'])
def delete_account():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'You need to be logged in to delete your account'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    try:
        # Remove friendships involving this user
        Friendship.query.filter((Friendship.user_id == user_id) | (Friendship.friend_id == user_id)).delete()
        
        # Delete user account
        db.session.delete(user)
        db.session.commit()

        session.pop('user_id', None)  # Log the user out after deletion

        return jsonify({'message': 'Account deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'An error occurred while deleting the account: {str(e)}'}), 500
    
@main_routes.route('/add_friend', methods=['POST'])
def add_friend():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid JSON format'}), 400
    
    friend_username = data.get('friend_username')

    if not friend_username:
        return jsonify({'message': 'Missing required fields'}), 400

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'You need to be logged in to add friends'}), 401

    friend = User.query.filter(db.func.lower(User.username) == db.func.lower(friend_username)).first()
    if not friend:
        return jsonify({'message': 'User not found'}), 404

    if user_id == friend.id:
        return jsonify({'message': 'You cannot add yourself as a friend'}), 400

    existing_friendship = Friendship.query.filter(
        ((Friendship.user_id == user_id) & (Friendship.friend_id == friend.id)) |
        ((Friendship.user_id == friend.id) & (Friendship.friend_id == user_id))
    ).first()

    if existing_friendship:
        if existing_friendship.status == 'pending':
            return jsonify({'message': 'Friend request is already pending'}), 400
        elif existing_friendship.status == 'accepted':
            return jsonify({'message': 'You are already friends with this user'}), 400

    new_friendship = Friendship(user_id=user_id, friend_id=friend.id, status='pending')
    
    try:
        db.session.add(new_friendship)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'An error occurred while sending the friend request'}), 500

    return jsonify({'message': 'Friend request sent successfully'}), 200

@main_routes.route('/accept_friend', methods=['POST'])
def accept_friend():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid JSON format'}), 400

    friend_id = data.get('friend_id')

    if not friend_id:
        return jsonify({'message': 'Missing required fields'}), 400

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'You need to be logged in to accept friend requests'}), 401

    friendship = Friendship.query.filter_by(user_id=friend_id, friend_id=user_id, status='pending').first()
    if not friendship:
        return jsonify({'message': 'Friend request not found or already accepted'}), 404

    friendship.status = 'accepted'
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'An error occurred while accepting the friend request'}), 500

    return jsonify({'message': 'Friend request accepted successfully'}), 200

@main_routes.route('/decline_friend', methods=['POST'])
def decline_friend():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid JSON format'}), 400

    friend_id = data.get('friend_id')

    if not friend_id:
        return jsonify({'message': 'Missing required fields'}), 400

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'You need to be logged in to decline friend requests'}), 401

    friendship = Friendship.query.filter_by(user_id=friend_id, friend_id=user_id, status='pending').first()
    if not friendship:
        return jsonify({'message': 'Friend request not found or already accepted'}), 404

    try:
        db.session.delete(friendship)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'An error occurred while declining the friend request'}), 500

    return jsonify({'message': 'Friend request declined successfully'}), 200

@main_routes.route('/remove_friend', methods=['POST'])
def remove_friend():
    if not request.is_json:
        return jsonify({"message": "Invalid request format. Expected JSON."}), 400

    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid JSON format'}), 400
    
    friend_id = data.get('friend_id')

    if not friend_id:
        return jsonify({'message': 'Missing required fields'}), 400

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'You need to be logged in to remove friends'}), 401

    # Check for friendship in both directions
    friendship = Friendship.query.filter(
        ((Friendship.user_id == user_id) & (Friendship.friend_id == friend_id)) |
        ((Friendship.user_id == friend_id) & (Friendship.friend_id == user_id))
    ).first()

    if not friendship:
        return jsonify({'message': 'Friendship not found'}), 404

    try:
        db.session.delete(friendship)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'An error occurred while removing the friend: {str(e)}'}), 500

    return jsonify({'message': 'Friend removed successfully'}), 200

@main_routes.route('/incoming_friend_requests', methods=['GET'])
def incoming_friend_requests():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'You need to be logged in to view friend requests'}), 401

    pending_requests = Friendship.query.filter_by(friend_id=user_id, status='pending').all()

    requests_list = []
    for f in pending_requests:
        friend = User.query.get(f.user_id)
        requests_list.append({
            'username': friend.username,
            'id': friend.id,
            'profile_picture': friend.profile_picture
        })
        
    return jsonify({'incoming_requests': requests_list}), 200


@main_routes.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            user.is_online = False
            db.session.commit()
                
    session.pop('user_id', None)
    return redirect(url_for('main_routes.login'))


UPLOAD_FOLDER = 'static/images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_routes.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('main_routes.login'))

    if 'file' not in request.files:
        return redirect(url_for('main_routes.homepage'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('main_routes.homepage'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        user = User.query.get(user_id)
        user.profile_picture = filename
        db.session.commit()

    return redirect(url_for('main_routes.homepage'))