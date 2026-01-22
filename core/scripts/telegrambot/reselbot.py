import json
import os
import telebot
from telebot import types
import threading
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'reseller_config.json')

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def build_keyboard(menu_data):
    if not menu_data or 'buttons' not in menu_data:
        return types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton('Wait for config...'))
    
    is_inline = menu_data.get('type') == 'inline'
    
    if is_inline:
        markup = types.InlineKeyboardMarkup()
        for row in menu_data['buttons']:
            row_buttons = []
            for btn in row:
                action = btn.get('action', 'text')
                param = btn.get('param', '')
                
                if action == 'url':
                    if param.startswith('http') or param.startswith('https'):
                        row_buttons.append(types.InlineKeyboardButton(btn['text'], url=param))
                    else:
                        row_buttons.append(types.InlineKeyboardButton(btn['text'], callback_data="error:url"))
                else:
                    cb_data = f"a|{action}|{param}"
                    if len(cb_data.encode('utf-8')) > 64:
                        pass
                    row_buttons.append(types.InlineKeyboardButton(btn['text'], callback_data=cb_data))
            
            if row_buttons:
                markup.row(*row_buttons)
        return markup
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for row in menu_data['buttons']:
            row_buttons = [types.KeyboardButton(btn['text']) for btn in row]
            if row_buttons:
                 markup.row(*row_buttons)
        return markup

def main():
    config = load_config()
    while not config or not config.get('bot_token'):
        print("Bot token not configured. Waiting 30s...")
        time.sleep(30)
        config = load_config()

    bot = telebot.TeleBot(config['bot_token'])
    print(f"Bot started: {bot.get_me().first_name}")
    
    user_states = {}

    def get_menu(cfg, menu_id='main'):
        if 'menus' in cfg:
            return cfg['menus'].get(menu_id)
        if menu_id == 'main':
             kb_list = cfg.get('keyboard', [])
             return { "text": "Welcome", "buttons": kb_list, "type": "reply" }
        return None

    def process_text_variables(text, user):
        try:
             text = text.replace('{user}', user.first_name or "User")
             text = text.replace('{username}', f"@{user.username}" if user.username else "")
             text = text.replace('{id}', str(user.id))
        except: pass
        return text

    def send_menu(chat_id, menu_id, user):
        cfg = load_config()
        menu = get_menu(cfg, menu_id)
        if not menu:
            bot.send_message(chat_id, "Menu not found.")
            return

        user_states[chat_id] = menu_id
        markup = build_keyboard(menu)
        text = process_text_variables(menu.get('text', 'Menu'), user)
        image = menu.get('image')

        if image and (image.startswith('http') or os.path.exists(image)):
            try:
                bot.send_photo(chat_id, image, caption=text, reply_markup=markup, parse_mode='HTML')
            except Exception as e:
                print(f"Failed to send photo: {e}")
                bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

    @bot.message_handler(commands=['start'])
    def start(message):
        send_menu(message.chat.id, 'main', message.from_user)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('a|'))
    def handle_inline_action(call):
        parts = call.data.split('|')
        if len(parts) < 3: return
        
        action = parts[1]
        param = parts[2]
        user_id = call.message.chat.id
        cfg = load_config()
        
        if action == 'submenu':
            target = get_menu(cfg, param)
            if target:
                user_states[user_id] = param
                
                is_target_inline = target.get('type') == 'inline'
                text = process_text_variables(target.get('text', 'Menu'), call.from_user)
                markup = build_keyboard(target)
                image = target.get('image')
                
                current_has_media = (call.message.content_type == 'photo')
                
                if not is_target_inline:
                    bot.delete_message(user_id, call.message.message_id)
                    send_menu(user_id, param, call.from_user)
                    return

                try:
                    if image:
                        if current_has_media:
                            media = types.InputMediaPhoto(image, caption=text, parse_mode='HTML')
                            bot.edit_message_media(media, chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)
                        else:
                            bot.delete_message(user_id, call.message.message_id)
                            bot.send_photo(user_id, image, caption=text, reply_markup=markup, parse_mode='HTML')
                    else:
                        if current_has_media:
                             bot.delete_message(user_id, call.message.message_id)
                             bot.send_message(user_id, text, reply_markup=markup, parse_mode='HTML')
                        else:
                             bot.edit_message_text(text, chat_id=user_id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
                             
                except Exception as e:
                    print(f"Edit failed: {e}")
                    try: bot.delete_message(user_id, call.message.message_id)
                    except: pass
                    send_menu(user_id, param, call.from_user)
            else:
                 bot.answer_callback_query(call.id, "Menu not found")

        elif action == 'text':
            bot.answer_callback_query(call.id)
            txt = process_text_variables(param, call.from_user)
            bot.send_message(user_id, txt, parse_mode='HTML')
            
        elif action == 'payment':
            bot.answer_callback_query(call.id)
            prices = cfg.get('prices', {})
            price = prices.get(param, 0)
            bot.send_message(user_id, f"💳 Invoice: {param} - ${price}")
            
        elif action == 'profile':
            user_states[user_id] = 'profile'
            prof_menu = get_menu(cfg, 'profile')
            
            if prof_menu:
                text = process_text_variables(prof_menu.get('text'), call.from_user)
                markup = build_keyboard(prof_menu)
                image = prof_menu.get('image')
                has_media = (call.message.content_type == 'photo')

                if prof_menu.get('type') == 'inline':
                    if image:
                        if has_media: bot.edit_message_media(types.InputMediaPhoto(image, caption=text, parse_mode='HTML'), chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)
                        else: 
                            bot.delete_message(user_id, call.message.message_id)
                            bot.send_photo(user_id, image, caption=text, reply_markup=markup, parse_mode='HTML')
                    else:
                        if has_media:
                             bot.delete_message(user_id, call.message.message_id)
                             bot.send_message(user_id, text, reply_markup=markup, parse_mode='HTML')
                        else:
                             bot.edit_message_text(text, chat_id=user_id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
                else: 
                     bot.delete_message(user_id, call.message.message_id)
                     send_menu(user_id, 'profile', call.from_user)
            else:
                bot.answer_callback_query(call.id)
                msg = f"👤 Profile: {call.from_user.first_name} (ID: {user_id})"
                bot.send_message(user_id, msg)

        elif action == 'my_key':
            bot.answer_callback_query(call.id)
            bot.send_message(user_id, f"🔑 No active subscription found for {call.from_user.first_name}.")

    @bot.message_handler(content_types=['text'])
    def handle_reply_text(message):
        cfg = load_config()
        text = message.text
        user_id = message.chat.id
        
        current_menu_id = user_states.get(user_id, 'main')
        current_menu = get_menu(cfg, current_menu_id) or get_menu(cfg, 'main')
        
        action, action_param = None, None
        if current_menu:
             for row in current_menu.get('buttons', []):
                for btn in row:
                    if btn['text'] == text:
                        action = btn.get('action')
                        action_param = btn.get('param')
                        break
                if action: break
        
        if not action:
             main = get_menu(cfg, 'main')
             if main:
                for row in main.get('buttons', []):
                    for btn in row:
                        if btn['text'] == text:
                            action = btn.get('action')
                            action_param = btn.get('param')
                            break
                    if action: break
        
        if not action: return 
            
        if action == 'text':
             txt = process_text_variables(action_param, message.from_user)
             bot.send_message(user_id, txt, parse_mode='HTML')
             
        elif action == 'submenu':
             send_menu(user_id, action_param, message.from_user)
             
        elif action == 'payment':
             prices = cfg.get('prices', {})
             p = prices.get(action_param, "0")
             bot.send_message(user_id, f"Invoice: {action_param} (${p})")
             
        elif action == 'profile':
             if get_menu(cfg, 'profile'):
                 send_menu(user_id, 'profile', message.from_user)
             else:
                 bot.send_message(user_id, f"Profile: {user_id}")

        elif action == 'my_key':
             bot.send_message(user_id, f"🔑 No active subscription found for {message.from_user.first_name}.")
        
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Bot crash: {e}")
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()
