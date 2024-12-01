from flask import Flask
from flask_mysql_connector import MySQL
import os

mysql = MySQL()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    # Initialize extensions
    mysql.init_app(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.content import content_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(content_bp, url_prefix='/content')

    return app
