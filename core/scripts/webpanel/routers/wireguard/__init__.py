from fastapi import APIRouter
from . import wireguard

router = APIRouter()

router.include_router(wireguard.router)
