from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from .config import get_logger, setup_logging
from .core import setup_exception_handlers
from .routers import process_router, progress_router, download_router, misc_router
from .schemas import HealthResponse
from .services.queue_worker import start_queue_workers, stop_queue_workers

logger = get_logger(__name__)


def create_app() -> FastAPI:
    logger.info("Creating FastAPI application")
    
    app = FastAPI(
        title="Batch Highlighter API",
        description="API for batch document highlighting and annotation",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    setup_exception_handlers(app)
    
    api_prefix = "/api/v1"
    
    app.include_router(misc_router, prefix=api_prefix)
    app.include_router(process_router, prefix=api_prefix)
    app.include_router(progress_router, prefix=api_prefix)
    app.include_router(download_router, prefix=api_prefix)
    
    logger.info("Routers included successfully")
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("Application starting up...")
        try:
            await start_queue_workers()
            logger.info("Queue workers started successfully")
        except Exception as e:
            logger.error(f"Failed to start queue workers: {e}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutting down...")
        try:
            await stop_queue_workers()
            logger.info("Queue workers stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping queue workers: {e}")
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"code": "INTERNAL_ERROR", "message": str(exc)})
    
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        return HealthResponse(status="healthy", version="1.0.0", timestamp=datetime.now().isoformat())
    
    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        return {"ready": True, "status": "ready"}
    
    @app.get("/worker-info", tags=["Health"])
    async def worker_info():
        """Return information about the current worker process."""
        return {
            "pid": os.getpid(),
            "parent_pid": os.getppid(),
            "worker_count": None  # Will be set by uvicorn if available
        }
    
    logger.info("FastAPI application created successfully")
    
    return app
