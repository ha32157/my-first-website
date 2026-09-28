from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True) if settings.database_url.startswith("sqlite:///") else None
    init_db()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", description="AI-powered 7-day fitness plan generator")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)
app.router.lifespan_context = lifespan
