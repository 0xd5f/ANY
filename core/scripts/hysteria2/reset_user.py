import init_paths
import sys
from db.database import db

def reset_user(username):
    if db is None:
        print("Error: Database connection failed. Please ensure MongoDB is running.")
        return 1

    try:
        user = db.get_user(username)
        if not user:
            print(f"Error: User '{username}' not found in the database.")
            return 1

        result = db.collection.update_one(
            {'_id': username},
            {
                '$set': {
                    'status': 'On-hold',
                    'blocked': False
                },
                '$unset': {
                    'account_creation_date': "",
                    'download_bytes': "",
                    'upload_bytes': ""
                }
            }
        )

        if result.modified_count > 0:
            print(f"User '{username}' has been reset successfully.")
            return 0
        else:
            print(f"User '{username}' data was already in a reset state. No changes made.")
            return 0

    except Exception as e:
        print(f"An error occurred while resetting the user: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <username>")
        sys.exit(1)

    username_to_reset = sys.argv[1].lower()
    exit_code = reset_user(username_to_reset)
    sys.exit(exit_code)