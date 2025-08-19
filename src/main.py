from fastapi import FastAPI
from .users import router as users_router

app = FastAPI(title="Reliv Chats API")

app.include_router(users_router.router, prefix='/api')

@app.get("/")
def read_root():
    return {"message": "Welcome to the Reliv Chats API"}