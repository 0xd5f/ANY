import init_paths
import json
import sys
import os
import getopt
from db.database import db

def get_user_info(username):
    if db is None:
        print("Error: Database connection failed. Please ensure MongoDB is running.")
        return 1
        
    try:
        user_info = db.get_user(username)
        if user_info:
            print(json.dumps(user_info, indent=4))
            return 0
        else:
            print(f"User '{username}' not found in the database.")
            return 1
    except Exception as e:
        print(f"An error occurred while fetching user data: {e}")
        return 1

if __name__ == "__main__":
    username = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "u:", ["username="])
    except getopt.GetoptError as err:
        print(str(err))
        print(f"Usage: {sys.argv[0]} -u <username>")
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-u", "--username"):
            username = arg.lower()

    if not username:
        print(f"Usage: {sys.argv[0]} -u <username>")
        sys.exit(1)

    exit_code = get_user_info(username)
    sys.exit(exit_code)