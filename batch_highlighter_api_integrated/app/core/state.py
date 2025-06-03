from .config import logger

logger.info("Initializing processing state")

processing_state = {
    "running": False,
    "paused": False,
    "progress": 0.0,
    "status": "Idle",
    "logs": [],
    "combined_log": None,
    "unmatched_values": None,
    "dest_folder": "",
    "selected_color": "Yellow",
}

COLOR_PRESETS = {
    "Yellow": {"pdf_rgb": (1.0, 1.0, 0.2), "word_val": "yellow"},
    "Green":  {"pdf_rgb": (0.66, 1.0, 0.33), "word_val": "green"},
    "Cyan":   {"pdf_rgb": (0.4, 1.0, 1.0),  "word_val": "cyan"},
    "Pink":   {"pdf_rgb": (1.0, 0.6, 0.86), "word_val": "magenta"},
    "Blue":   {"pdf_rgb": (0.6, 0.85, 1.0), "word_val": "blue"},
    "Red":    {"pdf_rgb": (1.0, 0.55, 0.55), "word_val": "red"},
}
