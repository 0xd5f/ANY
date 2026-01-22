from fastapi import APIRouter, HTTPException
from ..schema.response import DetailResponse
from ..schema.config.security import ChangeCredentialsInputBody, TelegramAuthInputBody, TelegramAuthResponse, ChangeRootPathInputBody
import cli_api

router = APIRouter()

@router.post('/credentials', response_model=DetailResponse, summary='Change Admin Credentials')
async def change_credentials_api(body: ChangeCredentialsInputBody):
    try:
        if not body.username and not body.password:
             raise HTTPException(status_code=400, detail='Either username or password must be provided.')
        
        cli_api.reset_webpanel_credentials(body.username, body.password)
        return DetailResponse(detail='Credentials updated successfully. The panel is restarting...')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.get('/telegram-auth', response_model=TelegramAuthResponse, summary='Get Telegram 2FA Status')
async def get_telegram_auth_status_api():
    try:
        config = cli_api.get_webpanel_env_config()
        return TelegramAuthResponse(enabled=config.get('TELEGRAM_AUTH_ENABLED', False))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error: {str(e)}')

@router.get('/root-path', summary='Get Root Path')
async def get_root_path_api():
    try:
        path = cli_api.get_webpanel_root_path()
        return {"root_path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error: {str(e)}')

@router.post('/root-path', response_model=DetailResponse, summary='Change Root Path')
async def change_root_path_api(body: ChangeRootPathInputBody):
    try:
        new_val = body.root_path
        if body.action == 'random':
            new_val = 'random'
        elif body.action == 'off':
            new_val = 'off'
        elif body.action == 'set':
            if not new_val:
                 raise HTTPException(status_code=400, detail='Root path is required for "set" action.')
        else:
            raise HTTPException(status_code=400, detail='Invalid action.')

        cli_api.change_webpanel_root_path(new_val)
        return DetailResponse(detail='Root path updated. Panel is restarting...')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.post('/telegram-auth', response_model=DetailResponse, summary='Set Telegram 2FA Status')
async def set_telegram_auth_status_api(body: TelegramAuthInputBody):
    try:
        cli_api.set_webpanel_telegram_auth(body.enabled)
        status_str = "enabled" if body.enabled else "disabled"
        return DetailResponse(detail=f'Telegram 2FA {status_str} successfully. The panel is restarting...')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')
