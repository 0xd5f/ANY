import init_paths
import os
import sys
import json
import fcntl
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
from db.database import db
from hysteria2_api import Hysteria2Client
from paths import CONFIG_FILE

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s: [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

LOCKFILE = "/tmp/kick.lock"
MAX_WORKERS = 8
API_BASE_URL = 'http://127.0.0.1:25413'

def acquire_lock():
    try:
        lock_file = open(LOCKFILE, 'w')
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except IOError:
        logger.warning("Another instance is already running. Exiting.")
        sys.exit(1)

def get_secret():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return config.get('trafficStats', {}).get('secret')
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def kick_users_api(usernames, secret):
    try:
        client = Hysteria2Client(base_url=API_BASE_URL, secret=secret)
        client.kick_clients(usernames)
        logger.info(f"Successfully sent kick command for users: {', '.join(usernames)}")
    except Exception as e:
        logger.error(f"Error kicking users via API: {e}")

def process_user(user_doc):
    username = user_doc.get('_id')
    
    if not username or user_doc.get('blocked', False):
        return None

    account_creation_date = user_doc.get('account_creation_date')
    if not account_creation_date:
        return None

    should_block = False

    try:
        expiration_days = user_doc.get('expiration_days', 0)
        if expiration_days > 0:
            creation_date = datetime.datetime.strptime(account_creation_date, "%Y-%m-%d")
            expiration_date = creation_date + datetime.timedelta(days=expiration_days)
            if datetime.datetime.now() >= expiration_date:
                should_block = True
                logger.info(f"User {username} is expired.")

        if not should_block:
            max_download_bytes = user_doc.get('max_download_bytes', 0)
            if max_download_bytes > 0:
                total_bytes = user_doc.get('download_bytes', 0) + user_doc.get('upload_bytes', 0)
                if total_bytes >= max_download_bytes:
                    should_block = True
                    logger.info(f"User {username} has exceeded their traffic limit.")

        if should_block:
            return username
            
    except (ValueError, TypeError) as e:
        logger.error(f"Error processing user {username} due to invalid data: {e}")
    
    return None

def main():
    lock_file = acquire_lock()
    try:
        if db is None:
            logger.error("Database connection failed. Exiting.")
            sys.exit(1)

        secret = get_secret()
        if not secret:
            logger.error(f"Could not find secret in {CONFIG_FILE}. Exiting.")
            sys.exit(1)
            
        all_users = db.get_all_users()
        logger.info(f"Loaded {len(all_users)} users from the database for processing.")
            
        users_to_block = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_user = {executor.submit(process_user, user_doc): user_doc for user_doc in all_users}
            for future in future_to_user:
                result = future.result()
                if result:
                    users_to_block.append(result)
        
        if not users_to_block:
            logger.info("No users to block or kick.")
            return

        logger.info(f"Found {len(users_to_block)} users to block: {', '.join(users_to_block)}")
        
        for username in users_to_block:
            db.update_user(username, {'blocked': True})
        logger.info("Successfully updated user statuses to 'blocked' in the database.")

        batch_size = 50 
        for i in range(0, len(users_to_block), batch_size):
            batch = users_to_block[i:i + batch_size]
            kick_users_api(batch, secret)
                        
    except Exception as e:
        logger.error(f"An unexpected error occurred in main execution: {e}", exc_info=True)
        sys.exit(1)
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
        logger.info("Script finished.")


if __name__ == "__main__":
    main()