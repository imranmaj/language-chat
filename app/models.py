from datetime import datetime
from enum import Enum
from enum import unique
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from . import db
from . import login

user_conversation_link = db.Table(
    "user_conversation_link",
    db.Model.metadata,
    db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("conversation_id", db.Integer, db.ForeignKey("conversation.id")),
)

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    waiting_for_conversation_with_language = db.Column(db.String(32), index=True, default="NONE")

    conversations = db.relationship("Conversation", secondary=user_conversation_link, back_populates="users", lazy="dynamic")
    messages = db.relationship("Message", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def active_conversation(self):
        return self.conversations.filter(Conversation.active == True).first()

    def __repr__(self):
        return f"User(username={self.username}, email={self.email}, waiting_for_conversation_with_language={self.waiting_for_conversation_with_language})"

class Conversation(db.Model):
    __tablename__ = "conversation"
    id = db.Column(db.Integer, primary_key=True)

    start_timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    end_timestamp = db.Column(db.DateTime, index=True)
    active = db.Column(db.Boolean, default=True)
    language = db.Column(db.String(32))

    users = db.relationship("User", secondary=user_conversation_link, back_populates="conversations", lazy="dynamic")
    messages = db.relationship("Message", backref="conversation", lazy="dynamic")

    def deactivate(self):
        self.active = False
        self.end_timestamp = datetime.utcnow()

    def __repr__(self):
        return f"Conversation(users={self.users}, language={self.language}, start_timestamp={self.start_timestamp}, end_timestamp={self.end_timestamp}, {len(self.messages.all())} messages)"

class Message(db.Model):
    __tablename__ = "message"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    content = db.Column(db.String(500))

    def __repr__(self):
        return f"Message(user={self.user}, timestamp={self.timestamp}, content={self.content})"

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

@unique
class Languages(Enum):
    NONE = 0
    English = 1
    Chinese = 2
    Spanish = 3

db.create_all()
