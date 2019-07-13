from datetime import datetime
from functools import wraps
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask import flash
from flask import abort
from flask_login import current_user
from flask_login import login_user
from flask_login import logout_user
from flask_socketio import emit
from flask_socketio import join_room
from . import db
from . import flask_app as app
from . import socketio
from .models import User
from .models import Conversation
from .models import Message
from .models import Languages
from .globals import format_datetime
from .globals import other_conversation_member

def set_title(new_title):
    def decor(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            app.jinja_env.globals.update(title=f"Language chat | {new_title}")

            return func(*args, **kwargs)
        return wrapped
    return decor

def require_authentication(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("You must be logged in to view this page", "danger")
            return redirect(url_for("index"))

        return func(*args, **kwargs)
    return wrapped

def require_conversation(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not current_user.active_conversation():
            flash("You are not in a conversation", "danger")
            return redirect(url_for("index"))
        
        return func(*args, **kwargs)
    return wrapped

@app.route("/")
@set_title("Home")
def index():
    if current_user.is_authenticated and current_user.waiting_for_conversation_with_language != "NONE":
        flash(f"Looking for conversation in {current_user.waiting_for_conversation_with_language}", "primary")

    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
@set_title("Log in")
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Login successful", "success")
            return redirect(url_for("index"))
        else:
            flash("Incorrect username or password", "danger")
            return render_template("login.html")

@app.route("/logout")
@set_title("Log out")
@require_authentication
def logout():
    logout_user()
    flash("Logout successful", "success")
    return redirect(url_for("index"))

@app.route("/signup", methods=["GET", "POST"])
@set_title("Sign up")
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    elif request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_passsword = request.form["confirm_password"]

        error = False
        if not all((username, email, password, confirm_passsword)):
            flash("You must fill in all fields", "danger")
            error = True
        if User.query.filter_by(username=username).first():
            flash("Username is already taken", "danger")
            error = True
        if User.query.filter_by(email=email).first():
            flash("Email is already taken", "danger")
            error = True
        if password != confirm_passsword:
            flash("Passwords do not match", "danger")
            error = True
        if error:
            return render_template("signup.html")

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Signup successful! You may now log in with your new credentials", "success")
        return redirect(url_for("login"))

@app.route("/settings", methods=["GET", "POST"])
@set_title("Settings")
@require_authentication
def settings():
    if request.method == "GET":
        return render_template("settings.html")
    elif request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        error = False
        if not all((email, password, confirm_password)):
            flash("You must fill in all fields", "danger")
            error = True
        if User.query.filter((User.email == email) & (User.id != current_user.id)).first():
            flash("Email is already taken", "danger")
            error = True
        if password != confirm_password:
            flash("Passwords do not match", "danger")
            error = True
        if error:
            return render_template("settings.html")

        current_user.email = email
        current_user.set_password(password)
        db.session.commit()

        flash("Settings updated successfully", "success")
        return render_template("settings.html")

@app.route("/new-conversation", methods=["GET", "POST"])
@set_title("New conversation")
@require_authentication
def new_conversation():
    if request.method == "GET":
        return render_template("new-conversation.html", languages=[language.name for language in Languages if language != Languages.NONE])
    elif request.method == "POST":
        # cancel any active conversation
        if current_user.active_conversation():
            current_user.active_conversation().deactivate()

        language = request.form["language"]
        
        # check if there is anyone else looking for a conversation in the same language
        other_user = User.query.filter((User.waiting_for_conversation_with_language == language) & (User.id != current_user.id)).first()
        if other_user:
            # other user is not searching anymore
            other_user.waiting_for_conversation_with_language = "NONE"

            # put both of them in the same conversation
            conversation = Conversation(language=language)
            other_user.conversations.append(conversation)
            current_user.conversations.append(conversation)
            db.session.commit()
            return redirect(url_for("current_conversation"))
        else:
            # we are waiting for someone else with the same language
            current_user.waiting_for_conversation_with_language = language
            db.session.commit()
            return redirect(url_for("index"))

@app.route("/past-conversations")
@set_title("Past conversations")
@require_authentication
def past_conversations():
    # latest at the top
    conversations = reversed(current_user.conversations.filter(Conversation.active == False).all())

    return render_template("past-conversations.html", conversations=conversations)

@app.route("/conversation/<conversation_id>")
@set_title("View past conversation")
@require_authentication
def conversation(conversation_id):
    conversation = Conversation.query.filter_by(id=conversation_id).first()
    if not conversation:
        abort(404)
    if current_user not in conversation.users:
        abort(403)

    return render_template("conversation.html", messages=conversation.messages)

LOAD_MESSAGE_COUNT = -100
@app.route("/conversation/current")
@set_title("Current conversation")
@require_authentication
@require_conversation
def current_conversation():
    conversation = current_user.active_conversation()
    messages = conversation.messages[:]

    global next_message
    next_message = len(messages) + LOAD_MESSAGE_COUNT - 1

    return render_template("current-conversation.html", messages=messages[LOAD_MESSAGE_COUNT:])

@socketio.on("connect")
@require_authentication
@require_conversation
def connect():
    join_room(get_room())

@socketio.on("load-previous-message")
@require_authentication
@require_conversation
def load_message(data):
    global next_message

    if next_message >= 0:
        scroll = data["scroll"]
        conversation = current_user.active_conversation()
        message = message_to_dict(conversation.messages[next_message], scroll)
        
        emit("receive-previous-message", message)
        next_message -= 1

@socketio.on("send-message")
@require_authentication
@require_conversation
def send_message(message):
    message = Message(content=message, user=current_user)

    current_user.active_conversation().messages.append(message)
    db.session.commit()
    emit("receive-new-message", message_to_dict(message, scroll=False), room=get_room())

@app.after_request
def cache_control(response):
    # no caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    return response

def message_to_dict(message, scroll):
    return {
        "username": message.user.username,
        "timestamp": format_datetime(message.timestamp),
        "content": message.content,
        "scroll": scroll
    }

def get_room():
    # make unique room based on user ids
    other_user = other_conversation_member(current_user.active_conversation())
    return f"{min(current_user.id, other_user.id)}-{max(current_user.id, other_user.id)}"
