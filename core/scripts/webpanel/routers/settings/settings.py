from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from dependency import get_templates
from config.config import CONFIGS

router = APIRouter()


@router.get('/')
async def settings(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    return templates.TemplateResponse('settings.html', {'request': request, 'api_token': CONFIGS.API_TOKEN})


@router.get('/config')
async def config(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    return templates.TemplateResponse('config.html', {'request': request})


@router.get('/nodes')
async def nodes(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    panel_url = str(request.base_url).rstrip('/')
    return templates.TemplateResponse('nodes.html', {'request': request, 'api_token': CONFIGS.API_TOKEN, 'panel_url': panel_url})


@router.get('/hysteria')
async def hysteria_settings(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    return templates.TemplateResponse('hysteria_settings.html', {'request': request})