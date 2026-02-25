from fastapi import APIRouter
from . import user
from . import server
from . import config
from . import ssl
from . import wireguard
from . import proxy

api_v1_router = APIRouter()

api_v1_router.include_router(user.router, prefix='/users', tags=['API - Users'])
api_v1_router.include_router(server.router, prefix='/server', tags=['API - Server'])
api_v1_router.include_router(config.router, prefix='/config')
api_v1_router.include_router(ssl.router, prefix='/ssl', tags=['API - SSL'])
api_v1_router.include_router(wireguard.router, prefix='/wireguard', tags=['API - Wireguard'])
api_v1_router.include_router(proxy.router, prefix='/proxy', tags=['API - Proxy'])