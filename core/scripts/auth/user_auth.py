import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from aiohttp import web
from pymongo import MongoClient

# Configuration
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "blitz_panel"
COLLECTION_NAME = "users"
HOST = "127.0.0.1"
PORT = 28262

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AuthServer")

# MongoDB Client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
users_collection = db[COLLECTION_NAME]

async def check_user(username, password):
    loop = asyncio.get_running_loop()
    def query():
        return users_collection.find_one({"_id": username})
    
    user = await loop.run_in_executor(None, query)
    
    if not user:
        return False, "User not found"
    
    if user.get("blocked", False):
        return False, "User is blocked"
    
    # Simple string comparison as per original Go code
    if user.get("password") != password:
        return False, "Invalid password"
    
    if user.get("unlimited_user", False):
         return True, "Unlimited user"

    # Expiration Check
    expiration_days = user.get("expiration_days", 0)
    if expiration_days > 0:
        creation_date_str = user.get("account_creation_date")
        if creation_date_str:
            try:
                creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d")
                expiration_date = creation_date + timedelta(days=expiration_days)
                if datetime.now() >= expiration_date:
                    return False, "Account expired"
            except ValueError:
                pass 

    # Traffic Check
    max_bytes = user.get("max_download_bytes", 0)
    if max_bytes > 0:
        current_up = user.get("upload_bytes", 0)
        current_down = user.get("download_bytes", 0)
        if (current_up + current_down) >= max_bytes:
             return False, "Data limit exceeded"
             
    return True, "OK"

async def auth_handler(request):
    try:
        data = await request.json()
        auth_str = data.get("auth")
        
        if not auth_str:
            return web.json_response({"ok": False, "msg": "Missing auth"}, status=400)
            
        try:
            username, password = auth_str.split(":", 1)
        except ValueError:
            return web.json_response({"ok": False, "msg": "Invalid auth format"}, status=400)
            
        is_valid, msg = await check_user(username, password)
        
        if is_valid:
            return web.json_response({"ok": True, "id": username})
        else:
            return web.json_response({"ok": False, "msg": msg}, status=401)
            
    except Exception as e:
        logger.error(f"Error handling auth: {e}")
        return web.json_response({"ok": False, "msg": "Internal Error"}, status=500)

app = web.Application()
app.add_routes([web.post('/auth', auth_handler)])

if __name__ == '__main__':
    print(f"Starting Auth Server on {HOST}:{PORT}")
    web.run_app(app, host=HOST, port=PORT)
