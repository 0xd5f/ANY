import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates

from dependency import get_templates
import cli_api

router = APIRouter()

@router.get('/')
async def wireguard_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    try:
        status = cli_api.wireguard_status() or {}
        is_installed = status.get("installed", False)
        clients = []
        if is_installed:
            clients = cli_api.wireguard_list_clients() or []
            
        return templates.TemplateResponse(
            'wireguard.html',
            {
                'request': request,
                'is_installed': is_installed,
                'status': status,
                'clients': clients
            }
        )
    except Exception as e:
        logging.error(f"Error loading wireguard page: {e}")
        raise HTTPException(status_code=500, detail=str(e))
