import json
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.database import db

def migrate():
    users_json_path = Path("/etc/hysteria/users.json")
    
    if not users_json_path.exists():
        print("users.json not found, no migration needed.")
        return

    if db is None:
        print("Error: Database connection failed. Cannot perform migration.", file=sys.stderr)
        sys.exit(1)

    try:
        with users_json_path.open('r') as f:
            users_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading or parsing users.json: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(users_data)} users in users.json to migrate.")
    migrated_count = 0

    for username, data in users_data.items():
        try:
            user_doc = {
                "_id": username.lower(),
                "password": data.get("password"),
                "max_download_bytes": data.get("max_download_bytes", 0),
                "expiration_days": data.get("expiration_days", 0),
                "account_creation_date": data.get("account_creation_date"),
                "blocked": data.get("blocked", False),
                "unlimited_user": data.get("unlimited_user", False),
                "status": data.get("status", "Offline"),
                "upload_bytes": data.get("upload_bytes", 0),
                "download_bytes": data.get("download_bytes", 0),
            }
            
            if user_doc["password"] is None:
                print(f"Warning: User '{username}' has no password, skipping.", file=sys.stderr)
                continue

            db.collection.update_one(
                {'_id': user_doc['_id']},
                {'$set': user_doc},
                upsert=True
            )
            migrated_count += 1
            print(f"  - Migrated user: {username}")
        
        except Exception as e:
            print(f"Error migrating user '{username}': {e}", file=sys.stderr)

    print(f"Migration complete. {migrated_count} users successfully migrated to MongoDB.")
    
    try:
        migrated_file_path = users_json_path.with_name("users.json.migrated")
        users_json_path.rename(migrated_file_path)
        print(f"Renamed old user file to: {migrated_file_path}")
    except OSError as e:
        print(f"Warning: Could not rename users.json: {e}", file=sys.stderr)

if __name__ == "__main__":
    migrate()