import init_paths
import sys
import json
from pathlib import Path
from hysteria2_api import Hysteria2Client
from db.database import db
from paths import CONFIG_FILE, API_BASE_URL

def get_secret() -> str | None:
    if not CONFIG_FILE.exists():
        return None
    try:
        with CONFIG_FILE.open('r') as f:
            config_data = json.load(f)
        return config_data.get("trafficStats", {}).get("secret")
    except (json.JSONDecodeError, IOError):
        return None

def get_users_from_db() -> list:
    if db is None:
        print("Error: Database connection failed.", file=sys.stderr)
        return []
    try:
        users = db.get_all_users()
        for user in users:
            user['username'] = user.pop('_id')
        return users
    except Exception as e:
        print(f"Error retrieving users from database: {e}", file=sys.stderr)
        return []

def main():
    users_list = get_users_from_db()
    if not users_list:
        print(json.dumps([], indent=2))
        return

    secret = get_secret()

    if secret:
        try:
            client = Hysteria2Client(base_url=API_BASE_URL, secret=secret)
            online_clients = client.get_online_clients()

            users_dict = {user['username']: user for user in users_list}
            for username, status in online_clients.items():
                if status.is_online and username in users_dict:
                    users_dict[username]['online_count'] = status.connections

            users_list = list(users_dict.values())

        except Exception as e:
            print(f"Warning: Could not connect to Hysteria2 API to get online status. {e}", file=sys.stderr)
            pass

    for user in users_list:
        user.setdefault('online_count', 0)
        
        if user.get('online_count', 0) > 0:
            user['status'] = 'Online'
        elif user.get('blocked'):
            user['status'] = 'Disabled'
        else:
            user['status'] = 'Offline'

    print(json.dumps(users_list, indent=2))

if __name__ == "__main__":
    main()