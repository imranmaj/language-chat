import datetime
from enum import Enum
from enum import unique
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from . import db
from . import login

association_table = db.Table(
    "association",
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
    conversations = db.relationship("Conversation", secondary=association_table, back_populates="users")
    messages = db.relationship("Message", backref="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def active_conversation(self):
        conversations = sorted(self.conversations, key=lambda conversation: conversation.created_timestamp)
        if len(conversations) == 0:
            return None
            
        last_conversation = conversations[-1]
        if last_conversation.active:
            return last_conversation
        else:
            return None

    def __repr__(self):
        return f"User(username={self.username}, email={self.email}, waiting_for_conversation_with_language={self.waiting_for_conversation_with_language})"

class Conversation(db.Model):
    __tablename__ = "conversation"
    id = db.Column(db.Integer, primary_key=True)
    created_timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    
    active = db.Column(db.Boolean, default=True)
    language = db.Column(db.String(32))

    users = db.relationship("User", secondary=association_table, back_populates="conversations")
    messages = db.relationship("Message", backref="conversation")

class Message(db.Model):
    __tablename__ = "message"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    content = db.Column(db.String(500))

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
