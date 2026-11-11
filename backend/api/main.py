from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routes_data import router as data_router
from mde.errors import MdeError
from mde.settings import Settings, get_settings
from mde.store import FileRunStore


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Model Disagreement Explorer API", version="1.0.0")
    app.state.settings = settings or get_settings()
    app.state.store = FileRunStore(app.state.settings.data_dir)
    app.include_router(data_router)

    @app.exception_handler(MdeError)
    async def mde_error_handler(request: Request, error: MdeError) -> JSONResponse:
        return JSONResponse(
            status_code=error.http_status,
            content={
                "code": error.code,
                "message": error.message,
                "details": error.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "bad_request",
                "message": "The request body or parameters are invalid.",
                "details": {"errors": jsonable_encoder(error.errors())},
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        message = error.detail if isinstance(error.detail, str) else "The request could not be completed."
        return JSONResponse(
            status_code=error.status_code,
            content={
                "code": "not_found" if error.status_code == 404 else "http_error",
                "message": message,
                "details": {},
            },
            headers=error.headers,
        )

    return app


app = create_app()
