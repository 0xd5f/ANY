import init_paths
import sys
import os
import argparse
import re
from datetime import datetime
from db.database import db

def edit_user(username, new_username=None, new_password=None, traffic_gb=None, expiration_days=None, creation_date=None, blocked=None, unlimited_user=None, note=None):
    if db is None:
        print("Error: Database connection failed.", file=sys.stderr)
        return 1

    username_lower = username.lower()
    try:
        user_data = db.get_user(username_lower)
        if not user_data:
            print(f"Error: User '{username}' not found.", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error fetching user data: {e}", file=sys.stderr)
        return 1

    updates = {}

    if new_password:
        updates['password'] = new_password
    
    if traffic_gb is not None:
        updates['max_download_bytes'] = int(float(traffic_gb) * 1073741824)
        
    if expiration_days is not None:
        updates['expiration_days'] = int(expiration_days)

    if creation_date is not None:
        if creation_date.lower() == 'null':
            updates['account_creation_date'] = None
        else:
            updates['account_creation_date'] = creation_date
            
    if blocked is not None:
        updates['blocked'] = blocked

    if unlimited_user is not None:
        updates['unlimited_user'] = unlimited_user

    if note is not None:
        updates['note'] = note
        
    try:
        if updates:
            db.update_user(username_lower, updates)
            print(f"User '{username}' attributes updated successfully.")

        if new_username and new_username.lower() != username_lower:
            new_username_lower = new_username.lower()
            if db.get_user(new_username_lower):
                print(f"Error: Target username '{new_username}' already exists.", file=sys.stderr)
                return 1
            
            updated_user_data = db.get_user(username_lower)
            
            updated_user_data.pop('_id')
            updated_user_data['_id'] = new_username_lower

            db.collection.insert_one(updated_user_data)
            db.delete_user(username_lower)
            print(f"User '{username}' successfully renamed to '{new_username}'.")

        elif not updates and not (new_username and new_username.lower() != username_lower):
             print("No changes specified.")

    except Exception as e:
        print(f"An error occurred during update: {e}", file=sys.stderr)
        return 1
        
    return 0


def str_to_bool(val):
    if val.lower() in ('true', 'y', '1'):
        return True
    elif val.lower() in ('false', 'n', '0'):
        return False
    raise argparse.ArgumentTypeError('Boolean value expected (true/false, y/n, 1/0).')

def validate_date(date_str):
    if date_str.lower() == 'null':
        return date_str
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid date format. Expected YYYY-MM-DD or 'null'.")

def validate_username(username):
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise argparse.ArgumentTypeError("Username can only contain letters, numbers, and underscores.")
    return username


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edit a Hysteria2 user's details in the database.")
    parser.add_argument("username", type=validate_username, help="The current username of the user to edit.")
    parser.add_argument("--new-username", dest="new_username", type=validate_username, help="New username for the user.")
    parser.add_argument("--password", dest="new_password", help="New password for the user.")
    parser.add_argument("--traffic-gb", dest="traffic_gb", type=float, help="New traffic limit in GB (e.g., 50). Use 0 for unlimited.")
    parser.add_argument("--expiration-days", dest="expiration_days", type=int, help="New expiration in days from creation date (e.g., 30). Use 0 for unlimited.")
    parser.add_argument("--creation-date", dest="creation_date", type=validate_date, help="New creation date in YYYY-MM-DD format, or 'null' to reset to On-hold.")
    parser.add_argument("--blocked", type=str_to_bool, help="Set blocked status (true/false).")
    parser.add_argument("--unlimited", dest="unlimited_user", type=str_to_bool, help="Set unlimited user status for IP limits (true/false).")
    parser.add_argument("--note", help="New note for the user. To clear the note, provide an empty string.")

    args = parser.parse_args()

    sys.exit(edit_user(
        username=args.username,
        new_username=args.new_username,
        new_password=args.new_password,
        traffic_gb=args.traffic_gb,
        expiration_days=args.expiration_days,
        creation_date=args.creation_date,
        blocked=args.blocked,
        unlimited_user=args.unlimited_user,
        note=args.note
    ))