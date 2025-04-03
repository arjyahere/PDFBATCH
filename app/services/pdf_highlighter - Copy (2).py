import fitz  # PyMuPDF
import os
import re
import time
from typing import List, Tuple
from ..core.utils import now_ts, safe_filename
from ..core.state import processing_state


# -------------------------------------------------------
# TEXT EXTRACTION (UNCHANGED)
# -------------------------------------------------------
def extract_lines_from_page(page):
    lines = []
    try:
        data = page.get_text("dict")
        for block in data.get("blocks", []):
            if block.get("type", 0) != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                line_text = "".join([s.get("text", "") for s in spans]).strip()
                bbox = line.get("bbox", None)
                rect = fitz.Rect(bbox) if bbox else None
                if line_text:
                    lines.append((line_text, rect))
    except Exception:
        txt = page.get_text("text")
        if txt and txt.strip():
            lines.append((txt.strip(), page.rect))
    return lines


# -------------------------------------------------------
# COLUMN DETECTION
# -------------------------------------------------------
def detect_column_ranges(page) -> List[Tuple[float, float]]:
    words = page.get_text("words")
    if not words:
        return []

    xs = sorted({round(w[0], 1) for w in words})
    if len(xs) == 1:
        return [(xs[0], xs[0] + 200)]

    column_ranges = []
    for i in range(len(xs) - 1):
        mid = (xs[i] + xs[i + 1]) / 2.0
        column_ranges.append((xs[i] - 2.0, mid + 2.0))

    column_ranges.append((xs[-1] - 2.0, xs[-1] + 400.0))
    return column_ranges


def _assign_word_to_col(x0, column_ranges):
    for idx, (cx0, cx1) in enumerate(column_ranges):
        if cx0 <= x0 <= cx1:
            return idx

    dists = [abs((cx0 + cx1) / 2.0 - x0) for (cx0, cx1) in column_ranges]
    return int(min(range(len(dists)), key=lambda i: dists[i]))


# -------------------------------------------------------
# MAIN HIGHLIGHT FUNCTION (FULL + FIXED)
# -------------------------------------------------------
def pdf_highlight_file(path, values, col_name, color_rgb, original_filename):

    matches = 0
    logs_local = []
    start = now_ts()

    try:
        pdf = fitz.open(path)
    except Exception as e:
        logs_local.append({
            "File": os.path.basename(path),
            "Page/Paragraph": "",
            "Column": col_name,
            "Matched Value": "",
            "Timestamp": start,
            "Output File": "",
            "Note": f"Failed to open PDF: {e}"
        })
        return 0, logs_local, None

    # ---------------- NORMALIZERS ----------------
    def norm_text(t):
        return str(t).strip().lower().replace(",", "").replace(" ", "")

    def norm_digits(t):
        return re.sub(r"\D", "", str(t) or "")

    values_norm_digits = {
        norm_digits(v) for v in values
        if v and 8 <= len(norm_digits(v)) <= 14
    }

    detected_digits = set()

    # -------------------------------------------------------
    # PAGE LOOP
    # -------------------------------------------------------
    for pno in range(len(pdf)):

        if not processing_state.get("running", True):
            break

        page = pdf[pno]
        words = page.get_text("words")
        if not words:
            continue

        column_ranges = detect_column_ranges(page)
        if not column_ranges:
            continue

        rows = {}
        for (x0, y0, x1, y1, wtext, block, line, wno) in words:
            rows.setdefault((block, line), []).append((x0, y0, x1, y1, wtext))

        # ---------------- HEADER DETECTION ----------------
        target_col_index = None
        header_candidates = []

        ys = [w[1] for w in words]
        if ys:
            header_cutoff = sorted(ys)[min(10, max(1, int(len(ys) * 0.05)))]
            for (x0, y0, x1, y1, text, block, line, wno) in words:
                if y0 <= header_cutoff + 2.0:
                    header_candidates.append((x0, text))

        col_name_l = (col_name or "").strip().lower()

        for x0, text in header_candidates:
            t = str(text).lower()
            if col_name_l in t or any(k in t for k in ["uan", "esi", "esic", "pf"]):
                target_col_index = _assign_word_to_col(x0, column_ranges)
                break

        # ---------------- SAMPLING DETECTION ----------------
        if target_col_index is None:
            col_counts = [0] * len(column_ranges)
            for _, row_words in list(rows.items())[:200]:
                col_cells = {}
                for (x0, y0, x1, y1, wtext) in row_words:
                    col_idx = _assign_word_to_col(x0, column_ranges)
                    col_cells[col_idx] = col_cells.get(col_idx, "") + norm_digits(wtext)

                for col_idx, merged in col_cells.items():
                    if merged in values_norm_digits:
                        col_counts[col_idx] += 1

            target_col_index = int(max(range(len(col_counts)), key=lambda i: col_counts[i]))

        # ---------------- ROW MATCHING ----------------
        for key, row_words in rows.items():

            cell_digits = ""

            for (x0, y0, x1, y1, wtext) in row_words:
                col_idx = _assign_word_to_col(x0, column_ranges)
                if col_idx == target_col_index:
                    cell_digits += norm_digits(wtext)

            if not cell_digits:
                continue

            matched_value = None

            if cell_digits in values_norm_digits:
                matched_value = cell_digits
            else:
                for v in values_norm_digits:
                    if v in cell_digits or cell_digits in v:
                        matched_value = v
                        break

            if matched_value:

                detected_digits.add(matched_value)

                try:
                    x0 = min(w[0] for w in row_words)
                    y0 = min(w[1] for w in row_words)
                    x1 = max(w[2] for w in row_words)
                    y1 = max(w[3] for w in row_words)

                    rect = fitz.Rect(x0, y0, x1, y1)

                    # ---- FIXES (NO FEATURE LOSS) ----
                    rect = rect.intersect(page.rect)
                    rect = rect + (-1, -1, 1, 1)

                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=color_rgb)
                    annot.set_opacity(0.4)
                    annot.update()
                    # --------------------------------

                    matches += 1

                    logs_local.append({
                        "File": os.path.basename(path),
                        "Page/Paragraph": f"Page {pno+1}",
                        "Column": col_name,
                        "Matched Value": matched_value,
                        "Timestamp": now_ts(),
                        "Output File": "",
                        "Note": "Row highlighted"
                    })

                except Exception as e:
                    logs_local.append({
                        "File": os.path.basename(path),
                        "Page/Paragraph": f"Page {pno+1}",
                        "Column": col_name,
                        "Matched Value": matched_value,
                        "Timestamp": now_ts(),
                        "Output File": "",
                        "Note": f"Highlight error: {e}"
                    })

        # ---------------- GLOBAL PAGE FAIL-SAFE ----------------
        page_digits = norm_digits(page.get_text())

        for v in values_norm_digits:
            if v in page_digits and v not in detected_digits:
                detected_digits.add(v)
                logs_local.append({
                    "File": os.path.basename(path),
                    "Page/Paragraph": f"Page {pno+1}",
                    "Column": col_name,
                    "Matched Value": v,
                    "Timestamp": now_ts(),
                    "Output File": "",
                    "Note": "Global page-level detection"
                })

        while processing_state.get("paused", False) and processing_state.get("running", True):
            time.sleep(0.2)

    # -------------------------------------------------------
    # SAFE DESTINATION HANDLING
    # -------------------------------------------------------
    base = os.path.splitext(original_filename)[0]
    out_name = f"{safe_filename(base)}_Highlighted.pdf"

    base_dir = os.getcwd()
    out_folder = processing_state.get("dest_folder")

    if not out_folder or not str(out_folder).strip():
        out_folder = os.path.join(base_dir, "output")

    os.makedirs(out_folder, exist_ok=True)
    out_path = os.path.join(out_folder, out_name)

    # -------------------------------------------------------
    # SAFE PDF SAVE
    # -------------------------------------------------------
    try:
        if os.path.exists(out_path):
            os.remove(out_path)

        pdf.save(out_path, garbage=4, deflate=True, incremental=False)
        pdf.close()

        if not os.path.exists(out_path):
            raise RuntimeError("PDF save completed but file not found on disk!")

    except Exception as e:
        logs_local.append({
            "File": os.path.basename(path),
            "Page/Paragraph": "",
            "Column": col_name,
            "Matched Value": "",
            "Timestamp": start,
            "Output File": "",
            "Note": f"Failed to save PDF: {str(e)}"
        })
        return matches, logs_local, None

    for entry in logs_local:
        if entry["File"] == os.path.basename(path) and not entry["Output File"]:
            entry["Output File"] = os.path.basename(out_path)

    return matches, logs_local, out_path
