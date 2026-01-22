import json
import os
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
import aiofiles
from init_paths import *
from paths import *

users_data = {}
users_lock = asyncio.Lock()

async def load_users(app):
    global users_data
    async with users_lock:
        if os.path.exists(USERS_FILE):
            try:
                async with aiofiles.open(USERS_FILE, 'r') as f:
                    content = await f.read()
                    users_data = json.loads(content)
            except (IOError, json.JSONDecodeError):
                users_data = {}
        else:
            users_data = {}
    app['users_data'] = users_data

async def authenticate(request):
    global users_data
    try:
        data = await request.json()
        auth_str = data.get("auth")
        if not auth_str:
            return web.json_response({"ok": False, "msg": "Auth field missing"}, status=400)
        
        username, password = auth_str.split(":", 1)
    except (json.JSONDecodeError, ValueError, TypeError):
        return web.json_response({"ok": False, "msg": "Invalid request format"}, status=400)

    async with users_lock:
        user = users_data.get(username)

        if not user:
            return web.json_response({"ok": False, "msg": "User not found"}, status=401)

        if user.get("blocked", False):
            return web.json_response({"ok": False, "msg": "User is blocked"}, status=401)

        if user.get("password") != password:
            return web.json_response({"ok": False, "msg": "Invalid password"}, status=401)
        
        expiration_days = user.get("expiration_days", 0)
        if expiration_days > 0:
            creation_date_str = user.get("account_creation_date")
            if creation_date_str:
                creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d")
                expiration_date = creation_date + timedelta(days=expiration_days)
                if datetime.now() >= expiration_date:
                    return web.json_response({"ok": False, "msg": "Account expired"}, status=401)

        max_bytes = user.get("max_download_bytes", 0)
        if max_bytes > 0:
            current_up = user.get("upload_bytes", 0)
            current_down = user.get("download_bytes", 0)
            if (current_up + current_down) >= max_bytes:
                return web.json_response({"ok": False, "msg": "Data limit exceeded"}, status=401)

    return web.json_response({"ok": True, "id": username})

app = web.Application()
app.router.add_post("/auth", authenticate)
app.on_startup.append(load_users)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=28262)