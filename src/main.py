from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .users.router import router as users_router  
from .chats.router import router as chats_router
from .rag.router import router as rag_router
from .categories.router import router as category_router

app = FastAPI(
    title="RelivChats API",
    description="API for processing and analyzing WhatsApp chats with AI",
    version="1.0.0"
)

# Add CORS middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users_router, prefix='/api')
app.include_router(chats_router, prefix='/api')
app.include_router(rag_router, prefix='/api')
app.include_router(category_router, prefix='/api')  

@app.get("/")
def read_root():
    return {"message": "RelivChats API is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}