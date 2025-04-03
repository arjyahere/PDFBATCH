from docx import Document
from docx.oxml import parse_xml
import re, os, time
from ..core.utils import now_ts, safe_filename
from ..core.state import processing_state, COLOR_PRESETS

def docx_highlight_file(path, values, col_name, word_color_enum, original_filename):
    matches = 0
    logs_local = []
    start = now_ts()
    try:
        doc = Document(path)
    except Exception as e:
        logs_local.append({"File": os.path.basename(path), "Page/Paragraph": "", "Column": col_name,
                           "Matched Value": "", "Timestamp": start, "Output File": "",
                           "Note": f"Failed to open DOCX: {e}"})
        return 0, logs_local, None

    for pidx, para in enumerate(doc.paragraphs, start=1):
        if not processing_state["running"]:
            break
        text = para.text or ""
        if not text.strip():
            continue
        for val in values:
            flags = re.IGNORECASE if re.search(r"[A-Za-z]", val) else 0
            pattern = r"\b" + re.escape(val) + r"\b"
            if re.search(pattern, text, flags):
                try:
                    for run in para.runs:
                        highlight_xml = parse_xml(
                            rf'<w:highlight xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="{COLOR_PRESETS[processing_state.get("selected_color", "Yellow")]["word_val"]}"/>')
                        rPr = run._element.get_or_add_rPr()
                        rPr.append(highlight_xml)
                    matches += 1
                    logs_local.append({"File": os.path.basename(path),
                                       "Page/Paragraph": f"Para {pidx}: {text[:80]}",
                                       "Column": col_name, "Matched Value": val,
                                       "Timestamp": start, "Output File": "",
                                       "Note": "Exact match (DOCX paragraph)"})
                except Exception as e:
                    logs_local.append({"File": os.path.basename(path),
                                       "Page/Paragraph": f"Para {pidx}", "Column": col_name,
                                       "Matched Value": val, "Timestamp": start,
                                       "Output File": "", "Note": f"Highlight error: {e}"})
        while processing_state["paused"] and processing_state["running"]:
            time.sleep(0.2)

    base = os.path.splitext(original_filename)[0]
    out_name = f"{safe_filename(base)}_Highlighted.docx"
    out_folder = processing_state.get("dest_folder") or os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(out_folder, exist_ok=True)
    out_path = os.path.join(out_folder, out_name)
    try:
        doc.save(out_path)
    except Exception as e:
        logs_local.append({"File": os.path.basename(path), "Page/Paragraph": "",
                           "Column": col_name, "Matched Value": "",
                           "Timestamp": start, "Output File": "",
                           "Note": f"Failed to save DOCX: {e}"})
        return matches, logs_local, None

    for entry in logs_local:
        if entry["File"] == os.path.basename(path) and not entry["Output File"]:
            entry["Output File"] = os.path.basename(out_path)
    return matches, logs_local, out_path
