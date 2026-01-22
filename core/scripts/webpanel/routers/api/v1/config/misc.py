from fastapi import APIRouter, HTTPException
from ..schema.response import DetailResponse
import cli_api

router = APIRouter()


@router.post('/install-tcp-brutal', response_model=DetailResponse, summary='Install TCP Brutal')
async def install_tcp_brutal():
    try:
        cli_api.install_tcp_brutal()
        return DetailResponse(detail='TCP Brutal installed successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/update-geo/{country}', response_model=DetailResponse, summary='Update Geo files')
async def update_geo(country: str):

    try:
        cli_api.update_geo(country)
        return DetailResponse(detail='Geo updated successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')
