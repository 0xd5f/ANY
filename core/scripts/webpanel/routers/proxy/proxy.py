from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dependency import get_templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def proxy_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates)
):
    return templates.TemplateResponse("proxy.html", {
        "request": request,
        "active_page": "proxy"
    })
