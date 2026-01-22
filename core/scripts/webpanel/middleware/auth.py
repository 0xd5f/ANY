from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
from typing import Awaitable, Callable
from starlette.types import ASGIApp
from urllib.parse import quote

from exception_handler import exception_handler
from session import SessionManager
from config import CONFIGS


class AuthMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp, session_manager: SessionManager, api_token: str | None):
        super().__init__(app)
        self.__session_manager = session_manager
        self.__api_token = api_token

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        public_routes = [
            f'/{CONFIGS.ROOT_PATH}/login',
            f'/{CONFIGS.ROOT_PATH}/verify-2fa',
            f'/{CONFIGS.ROOT_PATH}/check-2fa-status',
            f'/{CONFIGS.ROOT_PATH}/robots.txt'
        ]
        
        if request.url.path in public_routes or '/assets/' in request.url.path:
            return await call_next(request)

        is_api_request = '/api/v1/' in request.url.path

        if is_api_request:
            if self.__api_token:
                if api_key := request.headers.get('Authorization'):
                    if api_key == self.__api_token:
                        return await call_next(request)
                    else:
                        return self.__handle_api_failure(status=401, detail="Invalid API token.")

        session_id = request.cookies.get("session_id")

        if not session_id:
            if is_api_request:
                return self.__handle_api_failure(status=401, detail="Unauthorized.")

            return self.__redirect_to_login(request)

        session_data = self.__session_manager.get_session(session_id)

        if not session_data:
            if is_api_request:
                return self.__handle_api_failure(status=401, detail="The session is invalid.")

            return self.__redirect_to_login(request)

        if session_data.expires_at < datetime.now(timezone.utc):
            if is_api_request:
                return self.__handle_api_failure(status=401, detail="The session has expired.")

            return self.__redirect_to_login(request)

        return await call_next(request)

    def __handle_api_failure(self, status: int, detail: str):
        exc = HTTPException(status_code=status, detail=detail)

        return exception_handler(exc)

    def __redirect_to_login(self, request: Request):
        redirect_url = str(request.url_for('login'))
        return RedirectResponse(url=redirect_url, status_code=302)
