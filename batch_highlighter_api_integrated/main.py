"""
Main entry point for the Batch Highlighter API.
"""
import uvicorn

from app.api import create_app
from app.config import setup_logging, get_logger


# Setup logging first
setup_logging()
logger = get_logger(__name__)

# Create application at module level for uvicorn
app = create_app()
logger.info("Application created successfully")


def main():
    """
    Main entry point.
    
    Starts the Uvicorn server with production-ready settings.
    """
    from app.config.settings import get_settings
    
    try:
        logger.info("Starting Batch Highlighter API")
        
        # Get settings
        settings = get_settings()
        
        # Determine if running in production
        is_production = settings.environment == "production"
        
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Starting Uvicorn server on host={settings.host}, port={settings.port}")
        logger.info(f"Worker count: {settings.workers}")
        
        # Build uvicorn config
        uvicorn_config = {
            "host": settings.host,
            "port": settings.port,
            "log_level": settings.logging.level.lower(),
            "workers": settings.workers,
        }
        
        # Production settings
        if is_production:
            # Disable reload in production
            uvicorn_config["reload"] = False
            # Access log enabled
            uvicorn_config["access_log"] = True
            logger.info("Running in production mode")
        else:
            # Development settings
            uvicorn_config["reload"] = settings.reload
            # Disable access log in development for cleaner output
            uvicorn_config["access_log"] = False
            logger.info("Running in development mode")
        
        # Start server
        uvicorn.run("main:app", **uvicorn_config)
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
