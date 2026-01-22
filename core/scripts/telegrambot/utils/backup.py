import telebot
import subprocess
import qrcode
import io
import json
import os
import shlex
import re
import time
import threading
from dotenv import load_dotenv
from telebot import types
from utils.command import *

load_dotenv()

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '💾 Backup Server')
def backup_server(message):
    bot.reply_to(message, "Starting backup. This may take a few moments...")
    bot.send_chat_action(message.chat.id, 'typing')
    
    backup_command = f"python3 {CLI_PATH} backup-hysteria"
    result = run_cli_command(backup_command)

    if "Error" in result:
        bot.reply_to(message, f"Backup failed: {result}")
        return


    try:
        files = [f for f in os.listdir(BACKUP_DIRECTORY) if f.endswith('.zip')]
        files.sort(key=lambda x: os.path.getctime(os.path.join(BACKUP_DIRECTORY, x)), reverse=True)
        latest_backup_file = files[0] if files else None
    except Exception as e:
        bot.reply_to(message, f"Failed to locate the backup file: {str(e)}")
        return
    
    if latest_backup_file:
        backup_file_path = os.path.join(BACKUP_DIRECTORY, latest_backup_file)
        with open(backup_file_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"Manual backup completed: {latest_backup_file}")
    else:
        bot.reply_to(message, "No backup file found after the backup process.")

def perform_and_send_backup():
    
    backup_command = f"python3 {CLI_PATH} backup-hysteria"
    result = run_cli_command(backup_command)

    if "Error" in result:
        print(f"Automatic backup failed: {result}")
        return

    try:
        files = [f for f in os.listdir(BACKUP_DIRECTORY) if f.endswith('.zip')]
        files.sort(key=lambda x: os.path.getctime(os.path.join(BACKUP_DIRECTORY, x)), reverse=True)
        latest_backup_file = files[0] if files else None
    except Exception as e:
        print(f"Failed to locate the backup file during automatic backup: {str(e)}")
        return
    
    if latest_backup_file:
        backup_file_path = os.path.join(BACKUP_DIRECTORY, latest_backup_file)
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "[]").strip('[]')
        admin_ids = [int(uid.strip()) for uid in admin_ids_str.split(',') if uid.strip()]
        
        if not admin_ids:
            print("No admin user IDs found for automatic backup.")
            return
            
        for admin_id in admin_ids:
            try:
                with open(backup_file_path, 'rb') as f:
                    bot.send_document(admin_id, f, caption=f"Automatic hourly backup: {latest_backup_file}")
                print(f"Automatic backup sent to admin: {admin_id}")
            except Exception as e:
                print(f"Failed to send automatic backup to admin {admin_id}: {e}")
    else:
        print("No backup file found after automatic backup process.")


def backup_scheduler():
    interval_hours_str = os.getenv("BACKUP_INTERVAL_HOUR")
    if not interval_hours_str or not interval_hours_str.isdigit() or int(interval_hours_str) <= 0:
        print("Automatic backup interval is not set or is invalid. Scheduler will not run.")
        return
        
    interval_hours = int(interval_hours_str)
    interval_seconds = interval_hours * 3600
    print(f"Automatic backup scheduler started. Interval: {interval_hours} hour(s).")
    
    while True:
        time.sleep(interval_seconds)
        perform_and_send_backup()

scheduler_thread = threading.Thread(target=backup_scheduler, daemon=True)
scheduler_thread.start()