"""FastAPI main application."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.db.connection import init_database, close_pool
from app.routes import (
    messages,
    contacts,
    summary,
    calendar,
    chat,
    tasks,
    health,
    admin,
    policydoc,
)
from app.routes.v1 import (
    stream_chat,
    chat_with_tools,
    conversations,
    prompts as v1_prompts,
    admin as v1_admin,
    scheduler,
    calendar as v1_calendar,
)
from app.api import chat as v1_chat_api
from app.routes.v1 import rag_with_provenance
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.metrics import metrics_middleware
from app.middleware.quota import quota_middleware

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    await init_database()
    
    # Force reload vector store on startup
    from app.clients.vectorstore.json_adapter import _json_store
    print(f"[Startup] Reloading vector store from: {_json_store.file_path}")
    _json_store.load()
    print(f"[Startup] Loaded {len(_json_store.vectors)} vectors on startup")
    
    # Start background cleanup task for agentic chat
    from app.agents import agentic_chat
    import asyncio
    agentic_chat.set_cleanup_task(asyncio.create_task(agentic_chat.start_cleanup_task()))
    
    # Infer tasks from inbox messages on startup (background)
    from app.services.task_inference import infer_tasks_from_messages
    asyncio.create_task(infer_tasks_from_messages(limit=50))
    print("[Startup] Triggered task inference from inbox messages")
    
    # Initialize APScheduler for reminders
    from app.scheduler.apscheduler_manager import get_scheduler
    get_scheduler()  # Initialize scheduler
    print("[Startup] APScheduler initialized")
    
    # Register scheduling tools
    from app.tools import scheduling_registry
    print("[Startup] Scheduling tools registered")
    
    yield
    
    # Shutdown
    cleanup_task = agentic_chat.get_cleanup_task()
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    
    # Shutdown scheduler
    from app.scheduler.apscheduler_manager import shutdown_scheduler
    shutdown_scheduler()
    
    await close_pool()


app = FastAPI(
    title="AI Chief-of-Staff API",
    description="Backend API for AI Chief-of-Staff application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)
app.middleware("http")(metrics_middleware)
app.middleware("http")(quota_middleware)

# Include routers
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(summary.router, prefix="/api/summary", tags=["summary"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(policydoc.router, prefix="/api/policydoc", tags=["policydoc"])

# V1 API routes
app.include_router(stream_chat.router, prefix="/api/v1", tags=["v1-streaming"])
app.include_router(chat_with_tools.router, prefix="/api/v1", tags=["v1-tools"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["v1-conversations"])
app.include_router(v1_prompts.router, prefix="/api/v1/prompts", tags=["v1-prompts"])
app.include_router(v1_admin.router, prefix="/api/v1/admin", tags=["v1-admin"])
app.include_router(rag_with_provenance.router, prefix="/api/v1", tags=["v1-rag"])
app.include_router(scheduler.router, prefix="/api/v1/scheduler", tags=["v1-scheduler"])
app.include_router(v1_calendar.router, tags=["v1-calendar"])
app.include_router(v1_chat_api.router, prefix="/api/v1/chat", tags=["v1-chat-new"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI Chief-of-Staff API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "3001"))
    uvicorn.run(app, host="0.0.0.0", port=port)

