"""
Application settings management.
Loads configuration from environment variables and .env file.
"""
import os
from pathlib import Path
from typing import List, Optional


def load_env_file() -> dict:
    """Load settings from .env file."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    env_vars = {}
    
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars


class DatabaseSettings:
    """Database configuration settings."""
    def __init__(self):
        env = load_env_file()
        self.enabled = env.get('DATABASE__ENABLED', 'false').lower() == 'true'
        self.type = env.get('DATABASE__TYPE', 'sqlite')
        self.sqlite_path = env.get('DATABASE__SQLITE_PATH', 'jobs/')
        self.redis_url = env.get('DATABASE__REDIS_URL', 'redis://localhost:6379')
    
    @property
    def full_sqlite_path(self) -> Path:
        """Get full path to SQLite database."""
        return get_project_root() / self.sqlite_path


class StorageSettings:
    """Storage configuration settings."""
    def __init__(self):
        env = load_env_file()
        self.base_output_dir = env.get('STORAGE__BASE_OUTPUT_DIR', 'app/output')
        self.temp_dir = env.get('STORAGE__TEMP_DIR', 'temp')
        self.max_file_size_mb = int(env.get('STORAGE__MAX_FILE_SIZE_MB', 100))
    
    @property
    def full_temp_dir(self) -> Path:
        """Get full path to temp directory."""
        return get_project_root() / self.temp_dir


class SecuritySettings:
    """Security configuration settings."""
    def __init__(self):
        env = load_env_file()
        origins = env.get('SECURITY__ALLOWED_ORIGINS', '*')
        self.allowed_origins = [o.strip() for o in origins.split(',')] if origins != '*' else ['*']
        self.api_key_enabled = env.get('SECURITY__API_KEY_ENABLED', 'false').lower() == 'true'
        self.api_key = env.get('SECURITY__API_KEY', '')


class HighlightSettings:
    """Highlight customization settings."""
    def __init__(self):
        env = load_env_file()
        self.padding = float(env.get('HIGHLIGHT_PADDING', 5.0))


class LoggingSettings:
    """Logging configuration settings."""
    def __init__(self):
        env = load_env_file()
        self.level = env.get('LOGGING__LEVEL', 'INFO')
        self.format = env.get('LOGGING__FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.file_path = env.get('LOGGING__FILE_PATH', 'logs/app.log')
        self.max_bytes = int(env.get('LOGGING__MAX_BYTES', 10 * 1024 * 1024))
        self.backup_count = int(env.get('LOGGING__BACKUP_COUNT', 5))


class Settings:
    """Main application settings."""
    def __init__(self):
        env = load_env_file()
        
        # Application settings
        self.app_name = env.get('APP_NAME', 'Batch Highlighter API')
        self.app_version = env.get('APP_VERSION', '1.0.0')
        self.debug = env.get('DEBUG', 'false').lower() == 'true'
        self.host = env.get('HOST', '0.0.0.0')
        self.port = int(env.get('PORT', 8000))
        self.reload = env.get('RELOAD', 'false').lower() == 'true'
        self.environment = env.get('ENVIRONMENT', 'development')
        self.workers = int(env.get('WORKERS', 8))
        
        # Nested settings
        self.database = DatabaseSettings()
        self.storage = StorageSettings()
        self.security = SecuritySettings()
        self.highlight = HighlightSettings()
        self.logging = LoggingSettings()


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parents[2]


def get_settings() -> Settings:
    """Load application settings from environment variables and .env file."""
    return Settings()


settings = get_settings()
