from fastapi import APIRouter, HTTPException, BackgroundTasks
import asyncio
from typing import List
import cli_api

router = APIRouter()

@router.post("/install")
def install_proxy(background_tasks: BackgroundTasks):
    # Run the installation in the background
    try:
        cli_api.execute_proxy_command("install")
        return {"status": "started", "message": "Installation started"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.delete("/uninstall")
def uninstall_proxy():
    try:
        cli_api.execute_proxy_command("uninstall")
        return {"status": "success", "message": "Uninstalled successfully"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def get_proxy_status():
    try:
         return cli_api.execute_proxy_command("status")
    except Exception as e:
         return {"installed": False, "active": False, "error": str(e)}

import os

def get_server_ip():
    env_file = '/etc/hysteria/.configs.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('IP4='):
                    return line.strip().split('=', 1)[1]
    return "Unknown"

@router.get("/users")
def get_proxy_users():
    try:
         users = cli_api.execute_proxy_command("list")
         if getattr(users, 'stdout', None):
             users = eval(users.stdout)
         server_ip = get_server_ip()
         for user in users:
             user["server_ip"] = server_ip
         return users
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.post("/users")
def add_proxy_user(user_data: dict):
    try:
         name = user_data.get("username")
         if not name:
             raise HTTPException(status_code=400, detail="Username is required")
         
         password = user_data.get("password")
         if password:
             return cli_api.execute_proxy_command("add", name, password)
         else:
             return cli_api.execute_proxy_command("add", name)
             
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{username}")
def remove_proxy_user(username: str):
    try:
         cli_api.execute_proxy_command("remove", username)
         return {"status": "success"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
def get_proxy_config():
    try:
        config_data = cli_api.execute_proxy_command("get_config")
        if getattr(config_data, 'stdout', None):
            return eval(config_data.stdout)
        return config_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config")
def save_proxy_config(config: dict):
    try:
        socks_port = str(config.get("socks_port", 1080))
        http_port = str(config.get("http_port", 3128))
        max_conns = str(config.get("max_conns", 5000))
        
        result = cli_api.execute_proxy_command("save_config", socks_port, http_port, max_conns)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
