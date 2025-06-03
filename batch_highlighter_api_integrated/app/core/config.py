import os
import logging
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(os.path.dirname(BASE_DIR), "output")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Logging configuration
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "logs", "app.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logger = logging.getLogger("batch_highlighter")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# File handler with rotation
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
file_handler.setFormatter(file_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)
