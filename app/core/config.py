import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(os.path.dirname(BASE_DIR), "output")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
