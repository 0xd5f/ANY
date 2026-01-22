from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class JSONErrorResponse(BaseModel):
    status: int
    detail: str


def setup_exception_handler(app: FastAPI):
    @app.exception_handler(HTTPException)
    async def http_exception_handler_wrapper(request: Request, exc: HTTPException):
        return exception_handler(exc)


def exception_handler(exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=JSONErrorResponse(status=exc.status_code, detail=exc.detail).model_dump(),
    )
