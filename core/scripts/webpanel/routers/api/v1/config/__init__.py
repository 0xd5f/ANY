from fastapi import APIRouter
from . import hysteria
from . import warp
from . import telegram
from . import normalsub
from . import singbox
from . import ip
from . import misc
from . import extra_config
from . import security

router = APIRouter()


router.include_router(hysteria.router, prefix='/hysteria', tags=['API - Config - Hysteria'])
router.include_router(warp.router, prefix='/warp', tags=['API - Config - Warp'])
router.include_router(telegram.router, prefix='/telegram', tags=['API - Config - Telegram'])
router.include_router(normalsub.router, prefix='/normalsub', tags=['API - Config - Normalsub'])
router.include_router(singbox.router, prefix='/singbox', tags=['API - Config - Singbox'])
router.include_router(ip.router, prefix='/ip', tags=['API - Config - IP'])
router.include_router(extra_config.router, prefix='/extra-config', tags=['API - Config - Extra Config'])
router.include_router(security.router, prefix='/security', tags=['API - Config - Security'])
router.include_router(misc.router, tags=['API - Config - Misc'])