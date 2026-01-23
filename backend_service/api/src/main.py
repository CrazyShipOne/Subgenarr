"""Main FastAPI application for the Video Subtitle Generation API."""

import sys
sys.path.append('/app/shared')
sys.path.append('/app/src')

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from shared import init_db
from api.routes import auth, media, tasks, history, system
from api.schemas import ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events."""
    # Startup
    logger.info("Starting API service")
    init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down API service")


# Create FastAPI application
app = FastAPI(
    title="Video Subtitle Generation API",
    description="API for automated subtitle generation using LLM technology",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for general errors
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error="Internal server error",
            error_code="INTERNAL_ERROR",
        ).dict()
    )


# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(system.router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Video Subtitle Generation API",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
