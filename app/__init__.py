import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from .config import Config

from .globals import utc_to_local
from .globals import format_datetime
from .globals import other_conversation_member

flask_app = Flask(__name__)
flask_app.config.from_object(Config)

flask_app.jinja_env.globals.update(utc_to_local=utc_to_local)
flask_app.jinja_env.globals.update(format_datetime=format_datetime)
flask_app.jinja_env.globals.update(other_conversation_member=other_conversation_member)

db = SQLAlchemy(flask_app)
login = LoginManager(flask_app)

from . import routes, models

def run():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
