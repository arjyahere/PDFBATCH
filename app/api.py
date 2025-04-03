from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import process_router, progress_router, control_router, download_router, misc_router

def create_app():
    app = FastAPI(title="Batch Highlighter API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # include routers
    app.include_router(misc_router.router)
    app.include_router(process_router.router)
    app.include_router(progress_router.router)
    app.include_router(download_router.router)
    app.include_router(control_router.router)

    @app.get("/")
    async def root():
        return {"status": "Batch Highlighter API is running"}

    return app
