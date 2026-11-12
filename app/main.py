from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import models  # noqa: F401  (registers tables)
from .database import Base, engine
from .routers import auth, problems, submissions


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Online Judge", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(submissions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
