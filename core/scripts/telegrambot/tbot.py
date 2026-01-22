from telebot import types
import sys
import os

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(current_dir, '../db'))
    if db_path not in sys.path:
        sys.path.append(db_path)
    from database import Database
    db = Database(collection_name='auth_requests')
except Exception as e:
    print(f"Failed to connect to DB: {e}")
    db = None

from utils import *
import threading
import time

@bot.callback_query_handler(func=lambda call: call.data.startswith('auth_'))
def handle_auth_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized")
        return

    action, token = call.data.split(':')
    
    if action == 'auth_confirm':
        if db:
            result = db.collection.update_one(
                {"_id": token, "status": "pending"},
                {"$set": {"status": "approved"}}
            )
            if result.modified_count > 0:
                bot.edit_message_text(f"Login Approved ✅\nBy: {call.from_user.first_name}", call.message.chat.id, call.message.message_id)
                bot.answer_callback_query(call.id, "Login Approved")
            else:
                 bot.answer_callback_query(call.id, "Request expired or already processed")
        else:
             bot.answer_callback_query(call.id, "Database Error")

    elif action == 'auth_deny':
        if db:
            db.collection.update_one(
                {"_id": token},
                {"$set": {"status": "denied"}}
            )
            bot.edit_message_text(f"Login Denied ❌\nBy: {call.from_user.first_name}", call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "Login Denied")
        else:
             bot.answer_callback_query(call.id, "Database Error")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if is_admin(message.from_user.id):
        markup = create_main_markup()
        bot.reply_to(message, "Welcome to the User Management Bot!", reply_markup=markup)
    else:
        bot.reply_to(message, "Unauthorized access. You do not have permission to use this bot.")

def monitoring_thread():
    while True:
        monitor_system_resources()
        time.sleep(60)

if __name__ == '__main__':
    monitor_thread = threading.Thread(target=monitoring_thread, daemon=True)
    monitor_thread.start()
    version_thread = threading.Thread(target=version_monitoring, daemon=True)
    version_thread.start()
    bot.polling(none_stop=True)
