from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from dependency import get_templates
import json
import os
import subprocess
from pydantic import BaseModel
from typing import List, Optional, Any

from pathlib import Path

router = APIRouter()

current_dir = Path(__file__).resolve().parent
CONFIG_PATH = current_dir.parent.parent.parent / 'telegrambot' / 'reseller_config.json'

class Button(BaseModel):
    text: str
    action: str
    param: Optional[str] = None

class BotConfig(BaseModel):
    bot_token: Optional[str] = ""
    cryptobot_token: Optional[str] = ""
    prices: Optional[dict] = {}
    menus: Optional[dict] = {}
    keyboard: Optional[Any] = None
    messages: Optional[dict] = None

def load_config():
    default_config = {
        "bot_token": "",
        "cryptobot_token": "",
        "prices": {
            "1_day": 1.0,
            "7_days": 5.0,
            "30_days": 10.0,
            "90_days": 25.0,
            "365_days": 80.0
        },
        "menus": {
            "main": {
                "text": "Welcome! Choose an option:",
                "buttons": [
                    [{"text": "💳 Buy VPN", "action": "submenu", "param": "buy_menu"}, {"text": "🔑 My Key", "action": "my_key", "param": ""}],
                    [{"text": "📖 Instructions", "action": "text", "param": "This is a VPN bot..."}, {"text": "🆘 Support", "action": "text", "param": "Contact @admin"}]
                ],
                "type": "reply"
            },
            "buy_menu": {
                "text": "Select a plan:",
                "buttons": [
                    [{"text": "1 Day - $1.0", "action": "payment", "param": "1_day"}],
                    [{"text": "30 Days - $10.0", "action": "payment", "param": "30_days"}],
                    [{"text": "🔙 Back", "action": "submenu", "param": "main"}]
                ],
                "type": "inline"
            }
        }
    }
    
    if not os.path.exists(CONFIG_PATH):
        return default_config
        
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return default_config
            
            if 'menus' not in data:
                old_kb = data.get('keyboard', [])
                new_buttons = []
                for row in old_kb:
                    new_row = []
                    for btn in row.get('buttons', []):
                        if btn['action'] == 'support':
                            btn['action'] = 'text' 
                            btn['param'] = data.get('messages', {}).get('support_text', 'Contact @admin')
                        new_row.append(btn)
                    new_buttons.append(new_row)
                
                data['menus'] = {
                    "main": {
                        "text": data.get('messages', {}).get('welcome', "Welcome! Choose an option:"),
                        "buttons": new_buttons
                    }
                }
            
            if 'prices' not in data:
                data['prices'] = default_config['prices']
                
            return data
    except Exception:
        return default_config

def save_config(config_data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

@router.get('/')
async def reseller_page(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    config = load_config()
    return templates.TemplateResponse('reseller_bot.html', {'request': request, 'config': config})

@router.post('/save')
async def save_reseller_config(config: BotConfig):
    save_config(config.model_dump())
    return JSONResponse({"status": "success", "message": "Configuration saved successfully"})

SERVICE_NAME = 'hysteria-reseller-bot.service'
SERVICE_SOURCE_PATH = current_dir.parent.parent.parent / 'telegrambot' / SERVICE_NAME
SYSTEMD_PATH = Path('/etc/systemd/system/') / SERVICE_NAME

def install_service_if_missing():
    if os.name == 'nt': return
    
    res = subprocess.run(['systemctl', 'list-unit-files', SERVICE_NAME], capture_output=True, text=True)
    if SERVICE_NAME not in res.stdout:
        if not SERVICE_SOURCE_PATH.exists():
            return
            
        subprocess.run(['cp', str(SERVICE_SOURCE_PATH), str(SYSTEMD_PATH)], check=True)
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', 'enable', SERVICE_NAME], check=True)

@router.post('/start')
async def start_bot():
    try:
        install_service_if_missing()
        subprocess.run(['systemctl', 'start', 'hysteria-reseller-bot'], check=True)
        return JSONResponse({"status": "success", "message": "Bot started"})
    except Exception as e:
        if os.name == 'nt': 
             return JSONResponse({"status": "success", "message": "Bot started (Simulated on Windows)"})
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@router.post('/stop')
async def stop_bot():
    try:
        subprocess.run(['systemctl', 'stop', 'hysteria-reseller-bot'], check=True)
        return JSONResponse({"status": "success", "message": "Bot stopped"})
    except Exception as e:
        if os.name == 'nt': 
             return JSONResponse({"status": "success", "message": "Bot stopped (Simulated on Windows)"})
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@router.post('/restart')
async def restart_bot():
    try:
        subprocess.run(['systemctl', 'restart', 'hysteria-reseller-bot'], check=True)
        return JSONResponse({"status": "success", "message": "Bot restarted"})
    except Exception as e:
         if os.name == 'nt': 
             return JSONResponse({"status": "success", "message": "Bot restarted (Simulated on Windows)"})
         return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@router.get('/status')
async def bot_status():
    try:
        if os.name == 'nt':
            return JSONResponse({"status": "success", "active": True})
            
        result = subprocess.run(['systemctl', 'is-active', 'hysteria-reseller-bot'], capture_output=True, text=True)
        status = result.stdout.strip()
        return JSONResponse({"status": "success", "active": status == 'active'})
    except Exception:
        return JSONResponse({"status": "success", "active": False})
