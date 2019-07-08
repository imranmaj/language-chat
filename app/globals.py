import time
from datetime import datetime
from flask_login import current_user

def utc_to_local(utc_datetime):
    epoch = time.mktime(utc_datetime.timetuple())
    offset = datetime.fromtimestamp(epoch) - datetime.utcfromtimestamp(epoch)
    return utc_datetime + offset

def format_datetime(d):
    return d.strftime("%x %X")

def other_conversation_member():
    if current_user.active_conversation():
        users = current_user.active_conversation().users
        other_conversation_member = [user for user in users if user.username != current_user.username][0]
        
        return other_conversation_member
