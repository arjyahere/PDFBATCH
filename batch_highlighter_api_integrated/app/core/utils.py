from datetime import datetime

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_filename(s: str) -> str:
    return "".join(c for c in s if c.isalnum() or c in (" ", "_", "-", "(", ")")).rstrip()

def append_log(entry: dict, processing_state: dict):
    processing_state["logs"].append(entry)
