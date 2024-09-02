from flask_socketio import SocketIO, emit, disconnect
from flask import request
from app_factory import db
from models import User
import jwt

def setup_socketio(socketio):
    @socketio.on('connect')
    def handle_connect():
        token = request.args.get('token')
        if token:
            try:
                decoded = jwt.decode(token, 'your_secret_key', algorithms=['HS256'])
                user_id = decoded['user_id']
                user = User.query.get(user_id)
                if user:
                    user.is_online = True
                    db.session.commit()
                    emit('online_status', {'user_id': user_id, 'is_online': True}, broadcast=True)
            except jwt.ExpiredSignatureError:
                disconnect()
            except jwt.InvalidTokenError:
                disconnect()

    @socketio.on('disconnect')
    def handle_disconnect():
        token = request.args.get('token')
        if token:
            try:
                decoded = jwt.decode(token, 'your_secret_key', algorithms=['HS256'])
                user_id = decoded['user_id']
                user = User.query.get(user_id)
                if user:
                    user.is_online = False
                    db.session.commit()
                    emit('online_status', {'user_id': user_id, 'is_online': False}, broadcast=True)
            except jwt.ExpiredSignatureError:
                disconnect()
            except jwt.InvalidTokenError:
                disconnect()
