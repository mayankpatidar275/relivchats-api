from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .users.router import router as users_router  
from .chats.router import router as chats_router
from .rag.router import router as rag_router
from .categories.router import router as category_router
from .credits.router import router as credit_router
from .insights.router import router as insights_router

app = FastAPI(
    title="RelivChats API",
    description="API for processing and analyzing WhatsApp chats with AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix
app.include_router(users_router, prefix='/api')
app.include_router(chats_router, prefix='/api')
app.include_router(insights_router, prefix='/api')
app.include_router(rag_router, prefix='/api')
app.include_router(category_router, prefix='/api')
app.include_router(credit_router, prefix='/api')

@app.get("/")
def read_root():
    return {
        "message": "RelivChats API is running!",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}


## **Final API Structure**

# /api/chats
#   POST   /upload              # Upload chat file
#   GET    /                    # List user chats
#   GET    /{chat_id}           # Get chat details
#   PUT    /{chat_id}/display-name
#   GET    /{chat_id}/messages
#   GET    /{chat_id}/vector-status
#   DELETE /{chat_id}

# /api/insights                  # ← NEW
#   POST   /unlock               # Unlock insights (was in /credits)
#   GET    /jobs/{job_id}/status # Poll generation progress
#   GET    /chats/{chat_id}      # Get all insights for chat
#   POST   /{insight_id}/retry   # Retry failed insight

# /api/credits
#   GET    /balance
#   GET    /transactions
#   GET    /packages

# /api/categories
#   GET    /
#   GET    /{category_id}/insights

# /api/rag
#   POST   /query               # Conversational Q&A
#   POST   /generate            # Deprecated

# /api/users
#   POST   /store
#   DELETE /delete-account