"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import _get_engine
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Patent-KG Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def root():
    return {"status": "ok", "app": "Patent-KG Platform"}
