from fastapi import APIRouter, HTTPException
from ..schema.response import DetailResponse
from ..schema.config.telegram import StartInputBody, SetIntervalInputBody, BackupIntervalResponse, TelegramBotInfoResponse
import cli_api

router = APIRouter()


@router.get('/info', response_model=TelegramBotInfoResponse, summary='Get Telegram Bot Info')
async def telegram_info_api():
    try:
        info = cli_api.get_telegram_bot_info()
        return TelegramBotInfoResponse(**info)
    except Exception as e:
        return TelegramBotInfoResponse(error=str(e))


@router.post('/start', response_model=DetailResponse, summary='Start Telegram Bot')
async def telegram_start_api(body: StartInputBody):
    try:
        cli_api.start_telegram_bot(body.token, body.admin_id, body.backup_interval)
        return DetailResponse(detail='Telegram bot started successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.delete('/stop', response_model=DetailResponse, summary='Stop Telegram Bot')
async def telegram_stop_api():

    try:
        cli_api.stop_telegram_bot()
        return DetailResponse(detail='Telegram bot stopped successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/backup-interval', response_model=BackupIntervalResponse, summary='Get Telegram Bot Backup Interval')
async def telegram_get_interval_api():
    try:
        interval = cli_api.get_telegram_bot_backup_interval()
        return BackupIntervalResponse(backup_interval=interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error: {str(e)}')


@router.post('/backup-interval', response_model=DetailResponse, summary='Set Telegram Bot Backup Interval')
async def telegram_set_interval_api(body: SetIntervalInputBody):
    try:
        cli_api.set_telegram_bot_backup_interval(body.backup_interval)
        return DetailResponse(detail=f'Telegram bot backup interval set to {body.backup_interval} hours successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')