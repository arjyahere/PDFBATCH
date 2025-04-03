from docx.enum.text import WD_COLOR_INDEX

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
    "Yellow": {"pdf_rgb": (1.0, 1.0, 0.2), "word_val": "yellow", "docx_enum": WD_COLOR_INDEX.YELLOW},
    "Green":  {"pdf_rgb": (0.66, 1.0, 0.33), "word_val": "green", "docx_enum": WD_COLOR_INDEX.BRIGHT_GREEN},
    "Cyan":   {"pdf_rgb": (0.4, 1.0, 1.0),  "word_val": "cyan", "docx_enum": WD_COLOR_INDEX.TURQUOISE},
    "Pink":   {"pdf_rgb": (1.0, 0.6, 0.86), "word_val": "magenta", "docx_enum": WD_COLOR_INDEX.PINK},
    "Blue":   {"pdf_rgb": (0.6, 0.85, 1.0), "word_val": "blue", "docx_enum": WD_COLOR_INDEX.BLUE},
    "Red":    {"pdf_rgb": (1.0, 0.55, 0.55), "word_val": "red", "docx_enum": WD_COLOR_INDEX.RED},
}
