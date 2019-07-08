import time
from datetime import datetime
from flask_login import current_user
from .models import User

def format_datetime(utc_datetime):
    epoch = time.mktime(utc_datetime.timetuple())
    offset = datetime.fromtimestamp(epoch) - datetime.utcfromtimestamp(epoch)
    local_datetime = utc_datetime + offset
    return local_datetime.strftime("%x %I:%M:%S %p")

def other_conversation_member(conversation):
    return conversation.users.filter(User.id != current_user.id).first()
