from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
import os
from config import config

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()

def create_app(config_name=None):
    app = Flask(__name__)
    
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')
    app.config.from_object(config[config_name])
    
    app.secret_key = os.getenv('FLASK_SECRET_KEY', '0c52b4a010d36cf337abc234b7a6c345')  
    
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    
    from routes import main_routes
    app.register_blueprint(main_routes)
    
    with app.app_context():
        db.create_all()

    return app
