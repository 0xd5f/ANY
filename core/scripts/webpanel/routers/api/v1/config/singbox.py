from fastapi import APIRouter, HTTPException
from ..schema.response import DetailResponse
from ..schema.config.singbox import StartInputBody
import cli_api

router = APIRouter()


@router.post('/start', response_model=DetailResponse, summary='Start Singbox')
async def singbox_start_api(body: StartInputBody):
    try:
        cli_api.start_singbox(body.domain, body.port)
        return DetailResponse(detail='Singbox started successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.delete('/stop', response_model=DetailResponse, summary='Stop Singbox')
async def singbox_stop_api():

    try:
        cli_api.stop_singbox()
        return DetailResponse(detail='Singbox stopped successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

