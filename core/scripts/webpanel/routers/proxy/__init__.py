from fastapi import APIRouter
from . import proxy

router = APIRouter()

router.include_router(proxy.router)
