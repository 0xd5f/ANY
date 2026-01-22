from utils.command import *
from utils.common import create_main_markup, create_settings_markup

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '⚙️ Settings')
def settings_menu_handler(message):
    bot.send_message(message.chat.id, "⚙️ Settings Menu:", reply_markup=create_settings_markup())

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '⬅️ Back')
def back_to_main_menu_handler(message):
    bot.send_message(message.chat.id, "⬅️ Returning to Main Menu...", reply_markup=create_main_markup())