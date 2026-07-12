import os
import csv
import time
from datetime import datetime
from ..core.config import OUTPUT_FOLDER
from ..core.state import processing_state, COLOR_PRESETS
from ..core.utils import now_ts, append_log
from .pdf_highlighter import pdf_highlight_file
from .docx_highlighter import docx_highlight_file

def worker_process(data_in_order, doc_files, dest_folder, selected_columns, selected_color):
    processing_state["logs"].clear()
    processing_state["running"] = True
    processing_state["paused"] = False
    processing_state["progress"] = 0.0
    processing_state["status"] = "Starting..."
    processing_state["selected_color"] = selected_color

    base_folder = os.path.join(OUTPUT_FOLDER, dest_folder or "")
    os.makedirs(base_folder, exist_ok=True)
    processing_state["dest_folder"] = base_folder

    total_files = len(doc_files)

    for idx, fpath in enumerate(doc_files, start=1):
        if not processing_state["running"]:
            break
        processing_state["status"] = f"Processing {idx}/{total_files}: {os.path.basename(fpath)}"
        processing_state["progress"] = (idx-1)/total_files*100
        ext = os.path.splitext(fpath)[1].lower()
        if ext == ".pdf":
            original_name = os.path.basename(fpath).replace("temp_doc_", "")  # recover real name
            matches, logs_local, _ = pdf_highlight_file(fpath, data_in_order, selected_columns, COLOR_PRESETS[selected_color]["pdf_rgb"], original_name, idx)
        elif ext == ".docx":
            original_name = os.path.basename(fpath).replace("temp_doc_", "")
            matches, logs_local, _ = docx_highlight_file(
                fpath,
                data_in_order,
                selected_columns,
                COLOR_PRESETS[selected_color]["docx_enum"],
                original_name,
                idx
            )

        else:
            logs_local = [{"File": os.path.basename(fpath), "Page/Paragraph": "",
                            "Columns": selected_columns, "Matched Pair": "",
                            "Timestamp": now_ts(), "Output File": "",
                            "Note": "Unsupported file format - skipped"}]
        for r in logs_local:
            append_log(r, processing_state)
        processing_state["progress"] = idx/total_files*100

    combined_path = os.path.join(base_folder, f"Highlight_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    keys = ["File", "Page/Paragraph", "Columns", "Matched Pair", "Timestamp", "Output File", "Note"]
    with open(combined_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in processing_state["logs"]:
            writer.writerow({k: row.get(k, "") for k in keys})

    if isinstance(data_in_order[0], tuple) if data_in_order else False:
        # Pairs mode
        matched_pairs = set(tuple(log.get("Matched Pair", "").split(',')) if log.get("Matched Pair") else () for log in processing_state["logs"])
        unmatched = [p for p in data_in_order if p not in matched_pairs]
        unmatched_path = os.path.join(base_folder, f"Unmatched_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(unmatched_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([f"Unmatched Pairs from '{selected_columns}'"])
            w.writerow(["Column1", "Column2"])
            for p1, p2 in unmatched:
                w.writerow([p1, p2])
    else:
        # Single mode
        matched_values = set(log.get("Matched Value", "") for log in processing_state["logs"])
        unmatched = [v for v in data_in_order if v not in matched_values]
        unmatched_path = os.path.join(base_folder, f"Unmatched_values_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(unmatched_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([f"Unmatched Values from '{selected_columns}'"])
            for val in unmatched:
                w.writerow([val])

    processing_state.update({
        "running": False,
        "progress": 100.0,
        "status": f"Completed. Files: {len(doc_files)}. Log rows: {len(processing_state['logs'])}",
        "combined_log": combined_path,
        "unmatched_values": unmatched_path
    })

    # --- Clean Temporary Files ---
    try:
        for f in doc_files:
            if os.path.exists(f):
                os.remove(f)
    except Exception:
        pass
