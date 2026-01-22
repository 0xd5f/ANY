import init_paths
import sys
import argparse
import re
import secrets
import string
from datetime import datetime
from db.database import db

def add_bulk_users(traffic_gb, expiration_days, count, prefix, start_number, unlimited_user):
    if db is None:
        print("Error: Database connection failed. Please ensure MongoDB is running.")
        return 1
        
    try:
        traffic_bytes = int(float(traffic_gb) * 1073741824)
    except ValueError:
        print("Error: Traffic limit must be a numeric value.")
        return 1

    potential_usernames = []
    for i in range(count):
        username = f"{prefix}{start_number + i}"
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            print(f"Error: Generated username '{username}' contains invalid characters. Aborting.")
            return 1
        potential_usernames.append(username.lower())

    try:
        existing_docs = db.collection.find({"_id": {"$in": potential_usernames}}, {"_id": 1})
        existing_users_set = {doc['_id'] for doc in existing_docs}
    except Exception as e:
        print(f"Error querying database for existing users: {e}")
        return 1
        
    new_usernames = [u for u in potential_usernames if u not in existing_users_set]
    new_users_count = len(new_usernames)

    if new_users_count == 0:
        print("No new users to add. All generated usernames already exist.")
        return 0

    if count > new_users_count:
        print(f"Warning: {count - new_users_count} user(s) already exist. Skipping them.")

    alphabet = string.ascii_letters + string.digits
    passwords = [''.join(secrets.choice(alphabet) for _ in range(32)) for _ in range(new_users_count)]
    today_date = datetime.now().strftime("%Y-%m-%d")

    users_to_insert = []
    for i, username in enumerate(new_usernames):
        user_doc = {
            "_id": username,
            "password": passwords[i],
            "max_download_bytes": traffic_bytes,
            "expiration_days": expiration_days,
            "blocked": False,
            "unlimited_user": unlimited_user,
            "status": "Offline",
            "account_creation_date": today_date
        }
        users_to_insert.append(user_doc)

    try:
        db.collection.insert_many(users_to_insert, ordered=False)
        print(f"\nSuccessfully added {len(users_to_insert)} new users.")
        return 0
    except Exception as e:
        print(f"An unexpected error occurred during database insert: {e}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add bulk users to Hysteria2 via database.")
    parser.add_argument("-t", "--traffic-gb", dest="traffic_gb", type=float, required=True, help="Traffic limit for each user in GB.")
    parser.add_argument("-e", "--expiration-days", dest="expiration_days", type=int, required=True, help="Expiration duration for each user in days.")
    parser.add_argument("-c", "--count", type=int, required=True, help="Number of users to create.")
    parser.add_argument("-p", "--prefix", type=str, required=True, help="Prefix for usernames.")
    parser.add_argument("-s", "--start-number", type=int, default=1, help="Starting number for username suffix (default: 1).")
    parser.add_argument("-u", "--unlimited", action='store_true', help="Flag to mark users as unlimited (exempt from IP limits).")

    args = parser.parse_args()

    sys.exit(add_bulk_users(
        traffic_gb=args.traffic_gb,
        expiration_days=args.expiration_days,
        count=args.count,
        prefix=args.prefix,
        start_number=args.start_number,
        unlimited_user=args.unlimited
    ))