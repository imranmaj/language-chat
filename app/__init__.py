import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from .config import Config

flask_app = Flask(__name__)
flask_app.config.from_object(Config)

db = SQLAlchemy(flask_app)
login = LoginManager(flask_app)

from .globals import format_datetime
from .globals import other_conversation_member

flask_app.jinja_env.globals.update(format_datetime=format_datetime)
flask_app.jinja_env.globals.update(other_conversation_member=other_conversation_member)

from . import routes, models

def run():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
