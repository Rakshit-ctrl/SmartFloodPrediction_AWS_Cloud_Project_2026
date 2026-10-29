import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .database import ensure_schema
from .logging_config import setup_logging
from .routers import alerts, health, model, risk, satellite, weather
from .errors import ApiError

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()
    yield


app = FastAPI(
    title="Climate Risk and Smart Flood Prediction API",
    version="0.1.0",
    lifespan=lifespan,
    description="Prototype API; risk scores are not validated forecasts.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s: %s", request.method, request.url.path, type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Database error; the request was not saved."})


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, "code": exc.code}, headers=headers)


for r in (health.router, model.router, weather.router, risk.router, satellite.router, alerts.router):
    app.include_router(r)
