import json
import os
import sys
import fcntl
import datetime
import logging
from typing import Dict, Any, Optional, List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'scripts'))

from hysteria2_api import Hysteria2Client
from db.database import db

CONFIG_FILE = '/etc/hysteria/config.json'
API_BASE_URL = 'http://127.0.0.1:25413'
LOCKFILE = "/tmp/hysteria_traffic.lock"

STATUS_ONLINE = "Online"
STATUS_OFFLINE = "Offline"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def format_bytes(bytes_val: int) -> str:
    if not isinstance(bytes_val, (int, float)): return "0B"
    if bytes_val < 1024: return f"{bytes_val}B"
    if bytes_val < 1024**2: return f"{bytes_val / 1024:.2f}KB"
    if bytes_val < 1024**3: return f"{bytes_val / 1024**2:.2f}MB"
    if bytes_val < 1024**4: return f"{bytes_val / 1024**3:.2f}GB"
    return f"{bytes_val / 1024**4:.2f}TB"

def display_traffic_data(data: Dict[str, Dict[str, Any]]):
    if not data:
        print("No traffic data to display.")
        return

    green, cyan, nc = '\033[0;32m', '\033[0;36m', '\033[0m'
    headers = ["User", "Upload (TX)", "Download (RX)", "Status"]
    header_line = f"{headers[0]:<15} {headers[1]:<15} {headers[2]:<15} {headers[3]:<10}"
    separator = "-" * len(header_line)

    print("Traffic Data:")
    print(separator)
    print(header_line)
    print(separator)

    for user, entry in data.items():
        formatted_tx = format_bytes(entry.get("upload_bytes", 0))
        formatted_rx = format_bytes(entry.get("download_bytes", 0))
        status = entry.get("status", STATUS_OFFLINE)
        print(f"{user:<15} {green}{formatted_tx:<15}{nc} {cyan}{formatted_rx:<15}{nc} {status:<10}")
        print(separator)

class TrafficManager:
    def __init__(self, db_conn, api_base_url: str):
        self.db = db_conn
        if self.db is None:
            raise ValueError("Database connection is not available.")
        self.secret = self._get_secret()
        if not self.secret:
            raise ValueError(f"Secret not found or failed to read {CONFIG_FILE}.")
        self.client = Hysteria2Client(base_url=api_base_url, secret=self.secret)
        self.today_date = datetime.datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def _get_secret() -> Optional[str]:
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return config.get('trafficStats', {}).get('secret')
        except (json.JSONDecodeError, FileNotFoundError):
            logging.error(f"Could not read or parse secret from {CONFIG_FILE}")
            return None
            
    def _get_online_connection_count(self, user_status_from_api: Any) -> int:
        if not hasattr(user_status_from_api, 'is_online') or not user_status_from_api.is_online:
            return 0
        if not hasattr(user_status_from_api, 'connections'):
            return 1

        connections_attr = user_status_from_api.connections
        try:
            return len(connections_attr)
        except TypeError:
            return int(connections_attr) if isinstance(connections_attr, int) else 1

    def process_and_update_traffic(self) -> Dict[str, Any]:
        try:
            live_traffic = self.client.get_traffic_stats(clear=True)
            live_status = self.client.get_online_clients()
            
            if live_traffic is None or live_status is None:
                logging.error("Hysteria2 API returned None (Connection Error). Skipping update.")
                return {}

            db_users = {u['_id']: u for u in self.db.get_all_users()}
        except Exception as e:
            logging.error(f"Error communicating with Hysteria2 API or DB: {e}")
            return {}

        users_to_update: List[Tuple[str, Dict[str, Any]]] = []
        for username, user_data in db_users.items():
            updates = self._calculate_user_updates(username, user_data, live_traffic, live_status)
            if updates:
                users_to_update.append((username, updates))

        if users_to_update:
            for username, update_data in users_to_update:
                try:
                    self.db.update_user(username, update_data)
                    db_users[username].update(update_data)
                except Exception as e:
                    logging.error(f"Failed to update user {username} in DB: {e}")
        return db_users

    def _calculate_user_updates(self, username: str, user_data: Dict, live_traffic: Dict, live_status: Dict) -> Dict[str, Any]:
        updates = {}
        online_count = self._get_online_connection_count(live_status.get(username))
        
        has_traffic_now = False
        if username in live_traffic:
            updates['upload_bytes'] = user_data.get('upload_bytes', 0) + live_traffic[username].upload_bytes
            updates['download_bytes'] = user_data.get('download_bytes', 0) + live_traffic[username].download_bytes
            
            if live_traffic[username].upload_bytes > 0 or live_traffic[username].download_bytes > 0:
                has_traffic_now = True

        is_online = online_count > 0 or has_traffic_now
        
        if is_online and online_count == 0:
            online_count = 1

        if user_data.get('online_count') != online_count:
            updates['online_count'] = online_count

        is_activated = "account_creation_date" in user_data
        has_activity = is_online

        if not is_activated and has_activity:
            updates["account_creation_date"] = self.today_date
            updates["status"] = STATUS_ONLINE if is_online else STATUS_OFFLINE
        elif is_activated:
            new_status = STATUS_ONLINE if is_online else STATUS_OFFLINE
            if user_data.get("status") != new_status:
                updates["status"] = new_status
        elif not is_activated and not has_activity and user_data.get("status") != STATUS_OFFLINE:
            updates["status"] = STATUS_OFFLINE
            
        return updates

    def kick_expired_users(self):
        try:
            all_users = self.db.get_all_users()
        except Exception as e:
            logging.error(f"Failed to fetch users for expiration check: {e}")
            return

        now = datetime.datetime.now()
        users_to_kick, users_to_block = [], []
        
        for user in all_users:
            username = user.get('_id')
            if not username or user.get('blocked') or not user.get('account_creation_date'): continue

            try:
                total_bytes = user.get('download_bytes', 0) + user.get('upload_bytes', 0)
                expired_by_date = (user.get('expiration_days', 0) > 0 and now >= datetime.datetime.strptime(user['account_creation_date'], "%Y-%m-%d") + datetime.timedelta(days=user['expiration_days']))
                expired_by_traffic = (user.get('max_download_bytes', 0) > 0 and total_bytes >= user['max_download_bytes'])

                if expired_by_date or expired_by_traffic:
                    users_to_block.append(username)
                    if user.get("online_count", 0) > 0 or user.get("status") == STATUS_ONLINE:
                        users_to_kick.append(username)
            except (ValueError, TypeError): continue
        
        if users_to_block:
            for username in users_to_block:
                self.db.update_user(username, {'blocked': True, 'status': STATUS_OFFLINE, 'online_count': 0})
        
        if users_to_kick:
            for i in range(0, len(users_to_kick), 50):
                self._kick_api_call(users_to_kick[i:i+50])

    def _kick_api_call(self, usernames: List[str]):
        try:
            self.client.kick_clients(usernames)
            logging.info(f"Successfully kicked users: {', '.join(usernames)}")
        except Exception as e:
            logging.error(f"Failed to kick users via API: {e}")


def traffic_status(no_gui=False) -> Optional[Dict[str, Any]]:
    try:
        manager = TrafficManager(db_conn=db, api_base_url=API_BASE_URL)
        final_data = manager.process_and_update_traffic()
        if not no_gui:
            display_traffic_data(final_data)
        return final_data
    except ValueError as e:
        logging.critical(str(e))
        return None

def kick_expired_users():
    try:
        manager = TrafficManager(db_conn=db, api_base_url=API_BASE_URL)
        manager.kick_expired_users()
    except ValueError as e:
        logging.critical(str(e))

def main():
    lock_file = None
    try:
        lock_file = open(LOCKFILE, 'w')
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        args = sys.argv[1:]
        if "kick" in args:
            kick_expired_users()
        elif "--no-gui" in args:
            traffic_status(no_gui=True)
            kick_expired_users()
        else:
            traffic_status(no_gui=False)

    except IOError:
        logging.warning("Another instance of the script is already running.")
        sys.exit(1)
    finally:
        if lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()

if __name__ == "__main__":
    main()