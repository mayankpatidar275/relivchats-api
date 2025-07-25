from fastapi import FastAPI
from app.db import engine
from app import models
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables at startup
    models.Base.metadata.create_all(bind=engine)
    yield  # Nothing needed on shutdown

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"msg": "Connected to DB successfully!"}
