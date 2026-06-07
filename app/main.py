"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import all models so Base.metadata knows about them
from app.models.base import Base
from app.models import user, patent, task, quintuple, experiment  # noqa: F401


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

# Register API routers
from app.routes.auth import router as auth_router
from app.routes.patents import router as patents_router
from app.routes.tasks import router as tasks_router
from app.ws.progress import router as ws_router

app.include_router(auth_router)
app.include_router(patents_router)
app.include_router(tasks_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"status": "ok", "app": "Patent-KG Platform"}
