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

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    await init_database()
    
    # Start background cleanup task for agentic chat
    from app.agents import agentic_chat
    import asyncio
    agentic_chat.set_cleanup_task(asyncio.create_task(agentic_chat.start_cleanup_task()))
    
    yield
    
    # Shutdown
    cleanup_task = agentic_chat.get_cleanup_task()
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
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

