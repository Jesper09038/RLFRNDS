# app_factory.py
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_object='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register Blueprints
    from routes import main_routes
    app.register_blueprint(main_routes)

    @app.route('/login')
    def login():
        return send_from_directory('', 'index.html')

    @app.route('/signup')
    def signup():
        return send_from_directory('', 'index.html')

    with app.app_context():
        db.create_all()

    return app
