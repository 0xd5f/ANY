from fastapi import APIRouter, Depends, Form, Request, Body, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from hashlib import sha256
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import json
import uuid
import datetime
import sys
import os

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(current_dir, '../../../db'))
    if db_path not in sys.path:
        sys.path.append(db_path)
    from database import Database
    db = Database(collection_name='auth_requests')
except Exception as e:
    print(f"Failed to connect to DB: {e}")
    db = None

from dependency import get_templates, get_session_manager
from session import SessionManager
from config import CONFIGS

router = APIRouter()
pending_verifications = {}

@router.get('/login')
async def login(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    return templates.TemplateResponse('login.html', {'request': request})


@router.post('/login')
async def login_post(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates), session_manager: SessionManager = Depends(get_session_manager),
    username: str = Form(), password: str = Form()
):
    password_hash = sha256(password.encode()).hexdigest()
    if not username == CONFIGS.ADMIN_USERNAME or not password_hash == CONFIGS.ADMIN_PASSWORD:
        return templates.TemplateResponse('login.html', {'request': request, 'error': 'Invalid username or password'})

    if getattr(CONFIGS, 'TELEGRAM_AUTH_ENABLED', False):
        try:
            if CONFIGS.TELEGRAM_BOT_TOKEN and CONFIGS.TELEGRAM_ADMIN_IDS:
                code = str(random.randint(100000, 999999))
                token = str(uuid.uuid4())
                
                bot = telebot.TeleBot(CONFIGS.TELEGRAM_BOT_TOKEN)
                
                try:
                    admin_ids = json.loads(CONFIGS.TELEGRAM_ADMIN_IDS)
                except:
                    admin_ids = []

                if not isinstance(admin_ids, list):
                     admin_ids = [admin_ids]

                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("✅ Confirm Login", callback_data=f"auth_confirm:{token}"))
                markup.add(InlineKeyboardButton("❌ Deny", callback_data=f"auth_deny:{token}"))

                sent = False
                for user_id in admin_ids:
                    try:
                        bot.send_message(
                            user_id, 
                            f"🔐 *WebPanel Login Verification*\n\nUser: `{username}`\nIP: `{request.client.host}`\nCode: `{code}`", 
                            parse_mode='Markdown',
                            reply_markup=markup
                        )
                        sent = True
                    except Exception as e:
                        print(f"Failed to send to {user_id}: {e}")
                
                if sent:
                    data = {
                        'username': username,
                        'code': code,
                        'timestamp': datetime.datetime.now(),
                        'status': 'pending',
                        'token': token,
                        '_id': token
                    }
                    
                    if db:
                        try:
                            db.collection.insert_one(data)
                        except Exception as e:
                            print(f"DB Insert Error: {e}")
                            pending_verifications[token] = data
                    else:
                        pending_verifications[token] = data

                    return templates.TemplateResponse('verify_2fa.html', {'request': request, 'token': token})
                else:
                    return templates.TemplateResponse('login.html', {'request': request, 'error': 'Failed to send 2FA code. Check bot settings.'})
        except Exception as e:
            print(f"2FA Error: {e}")
            return templates.TemplateResponse('login.html', {'request': request, 'error': f'2FA Error: {str(e)}'})

    session_id = session_manager.set_session(username)
    redirect_url = request.url_for('index')
    res = RedirectResponse(url=redirect_url, status_code=302)
    res.set_cookie(key='session_id', value=session_id)
    return res

@router.post('/check-2fa-status')
async def check_2fa_status(
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
    token: str = Body(..., embed=True)
):
    data = None
    if db:
        data = db.collection.find_one({"_id": token})
    
    if not data:
        data = pending_verifications.get(token)

    if not data:
        return JSONResponse({'status': 'invalid'}, status_code=200)
    
    if (datetime.datetime.now() - data['timestamp']).total_seconds() > 300:
        return JSONResponse({'status': 'expired'}, status_code=200)

    if data['status'] == 'approved':
        session_id = session_manager.set_session(data['username'])
        if db:
            db.collection.delete_one({"_id": token})
        else:
            del pending_verifications[token]
            
        res = JSONResponse({'status': 'approved'})
        res.set_cookie(key='session_id', value=session_id, max_age=3600, path='/', httponly=True)
        return res
    
    elif data['status'] == 'denied':
        return JSONResponse({'status': 'denied'})
        
    return JSONResponse({'status': 'pending'})

@router.post('/verify-2fa')
async def verify_2fa(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates), 
    session_manager: SessionManager = Depends(get_session_manager),
    code: str = Form(), token: str = Form()
):
    verification = None
    if db:
        verification = db.collection.find_one({"_id": token})
    
    if not verification:
        verification = pending_verifications.get(token)

    if not verification:
        return templates.TemplateResponse('login.html', {'request': request, 'error': 'Session expired or invalid.'})
        
    if (datetime.datetime.now() - verification['timestamp']).total_seconds() > 300:
        return templates.TemplateResponse('login.html', {'request': request, 'error': 'Code expired.'})
        
    if verification['code'] != code.strip():
        return templates.TemplateResponse('verify_2fa.html', {'request': request, 'token': token, 'error': 'Invalid code.'})
        
    username = verification['username']
    if db:
        db.collection.delete_one({"_id": token})
    else:
        del pending_verifications[token]
    
    session_id = session_manager.set_session(username)
    redirect_url = request.url_for('index')
    res = RedirectResponse(url=redirect_url, status_code=302)
    res.set_cookie(key='session_id', value=session_id)
    return res




@router.get('/logout')
async def logout(request: Request, session_manager: SessionManager = Depends(get_session_manager)):
    session_id = request.cookies.get('session_id')
    if session_id:
        session_manager.revoke_session(session_id)

    res = RedirectResponse(url=request.url_for('index'), status_code=302)
    res.delete_cookie('session_id')
    return res
