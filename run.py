from app_factory import create_app, socketio

app = create_app()

if __name__ == '__main__':
    from socket_events import setup_socketio  # Import here to avoid circular import
    setup_socketio(socketio)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
