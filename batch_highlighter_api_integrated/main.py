from app.api import create_app
from app.core.config import logger

try:
    app = create_app()
    logger.info("Application created successfully")
except Exception as e:
    logger.error(f"Failed to create application: {e}")
    raise

if __name__ == "__main__":
    try:
        import uvicorn
        logger.info("Starting Uvicorn server on host 0.0.0.0 port 8000")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
