from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask import flash
from flask import abort
from flask_login import current_user
from flask_login import login_user
from flask_login import logout_user
from . import db
from . import flask_app as app
from .models import User
from .models import Conversation
from .models import Message
from .models import Languages

@app.route("/")
def index():
    if current_user.is_authenticated and current_user.waiting_for_conversation_with_language != "NONE":
        flash(f"Looking for conversation in {current_user.waiting_for_conversation_with_language}", "primary")

    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
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
def logout():
    if not current_user.is_authenticated:
        flash("You must be logged in to view this page", "danger")
        return redirect(url_for("index"))

    logout_user()
    flash("Logout successful", "success")
    return redirect(url_for("index"))

@app.route("/signup", methods=["GET", "POST"])
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
def settings():
    if not current_user.is_authenticated:
        flash("You must be logged in to view this page", "danger")
        return redirect(url_for("index"))    

    if request.method == "GET":
        return render_template("settings.html")
    elif request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        error = False
        if not all ((email, password, confirm_password)):
            flash("You must fill in all fields", "danger")
            error = True
        if User.query.filter_by(email=email).first() and User.query.filter_by(email=email).first().email != current_user.email:
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
def new_conversation():
    if not current_user.is_authenticated:
        flash("You must be logged in to view this page", "danger")
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("new-conversation.html", languages=[language.name for language in Languages if language != Languages.NONE])
    elif request.method == "POST":
        # cancel any active conversation
        if current_user.active_conversation():
            current_user.active_conversation().active = False
        current_user.waiting_for_conversation_with_language = "NONE"

        language = request.form["language"]
        
        # check if there is anyone else looking for a conversation in the same language
        other_user = User.query.filter_by(waiting_for_conversation_with_language=language).first()
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
def past_conversations():
    if not current_user.is_authenticated:
        flash("You must be logged in to view this page", "danger")
        return redirect(url_for("index"))

    conversations = reversed(current_user.conversations)
    displayed_conversations = []
    for conversation in conversations:
        if not conversation.active:
            displayed_conversations.append({
                "username": other_user(conversation).username,
                "language": conversation.language,
                "timestamp": conversation.created_timestamp,
                "id": conversation.id
            })

    return render_template("past-conversations.html", conversations=displayed_conversations)

@app.route("/conversation/<conversation_id>")
def conversation(conversation_id):
    if not current_user.is_authenticated:
        flash("You must be logged in to view this page", "danger")
        return redirect(url_for("index"))

    conversation = Conversation.query.filter_by(id=conversation_id).first()
    if not conversation:
        abort(404)
    if current_user not in conversation.users:
        abort(403)

    return render_template("conversation.html", messages=conversation.messages)

@app.route("/conversation/current")
def current_conversation():
    if not current_user.is_authenticated:
        flash("You must be logged in to view this page", "danger")
        return redirect(url_for("index"))
    if not current_user.active_conversation():
        flash("You are not in a conversation", "danger")
        return redirect(url_for("index"))

    conversation = current_user.active_conversation()
    return render_template("current-conversation.html", messages=conversation.messages, jump=True)

@app.route("/send-message", methods=["POST"])
def send_message():
    if not current_user.is_authenticated:
        flash("You must be logged in to view this page", "danger")
        return redirect(url_for("index"))
    if not current_user.active_conversation():
        flash("You are not in a conversation", "danger")
        return redirect(url_for("index"))

    message = request.form["message"]
    # attach message to conversation
    current_user.active_conversation().messages.append(Message(content=message, user=current_user))
    db.session.commit()
    return redirect(url_for("current_conversation"))

def other_user(conversation):
    all_users = conversation.users
    other_user = [user for user in all_users if current_user.username != user.username][0]
    return other_user
