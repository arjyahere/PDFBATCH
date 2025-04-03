import fitz  # PyMuPDF
import os
import re
import time
from typing import List, Tuple
from ..core.utils import now_ts, safe_filename
from ..core.state import processing_state


# -------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------
UAN_LENGTH = 12
ESI_LENGTH = 10
VALID_LENGTHS = (UAN_LENGTH, ESI_LENGTH)


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
# MAIN HIGHLIGHT FUNCTION
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
    def norm_digits(t):
        return re.sub(r"\D", "", str(t or ""))

    # Normalize input values (UAN / ESI only)
    values_norm_digits = set()
    for v in values:
        d = norm_digits(v)
        if len(d) in VALID_LENGTHS:
            values_norm_digits.add(d)

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
        header_cutoff = sorted(ys)[min(10, max(1, int(len(ys) * 0.05)))]

        for (x0, y0, x1, y1, text, block, line, wno) in words:
            if y0 <= header_cutoff + 2.0:
                header_candidates.append((x0, text))

        col_name_l = (col_name or "").lower()

        for x0, text in header_candidates:
            if col_name_l in str(text).lower():
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
        for row_words in rows.values():

            cell_digits = ""
            for (x0, y0, x1, y1, wtext) in row_words:
                if _assign_word_to_col(x0, column_ranges) == target_col_index:
                    d = norm_digits(wtext)
                    if d:
                        cell_digits += d

            if not cell_digits:
                continue

            matched_value = None
            for v in values_norm_digits:
                if cell_digits == v:
                    matched_value = v
                    break
                if len(cell_digits) > len(v) and v in cell_digits:
                    matched_value = v
                    break
                if len(cell_digits) < len(v) and cell_digits in v:
                    matched_value = v
                    break

            if not matched_value or matched_value in detected_digits:
                continue

            detected_digits.add(matched_value)

            try:
                cell_boxes = [
                    (x0, y0, x1, y1)
                    for (x0, y0, x1, y1, _) in row_words
                    if _assign_word_to_col(x0, column_ranges) == target_col_index
                ]

                if not cell_boxes:
                    continue

                x0 = min(b[0] for b in cell_boxes)
                y0 = min(b[1] for b in cell_boxes)
                x1 = max(b[2] for b in cell_boxes)
                y1 = max(b[3] for b in cell_boxes)

                rect = fitz.Rect(x0, y0, x1, y1)
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=color_rgb)
                annot.set_opacity(0.35)
                annot.update()

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
        page_text = page.get_text("text")
        page_digits = re.sub(r"\D", "", page_text)

        for v in values_norm_digits:
            if v in page_digits and v not in detected_digits:

                rects = page.search_for(v)
                for rect in rects:
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=color_rgb)
                    annot.set_opacity(0.35)
                    annot.update()
                    matches += 1

                detected_digits.add(v)

                logs_local.append({
                    "File": os.path.basename(path),
                    "Page/Paragraph": f"Page {pno+1}",
                    "Column": col_name,
                    "Matched Value": v,
                    "Timestamp": now_ts(),
                    "Output File": "",
                    "Note": "Global detection + highlight"
                })

        while processing_state.get("paused", False) and processing_state.get("running", True):
            time.sleep(0.2)

    # -------------------------------------------------------
    # SAVE OUTPUT
    # -------------------------------------------------------
    base = os.path.splitext(original_filename)[0]
    out_name = f"{safe_filename(base)}_Highlighted.pdf"

    out_folder = processing_state.get("dest_folder") or os.path.join(os.getcwd(), "output")
    os.makedirs(out_folder, exist_ok=True)

    out_path = os.path.join(out_folder, out_name)

    if os.path.exists(out_path):
        os.remove(out_path)

    pdf.save(out_path, garbage=4, deflate=True)
    pdf.close()

    for entry in logs_local:
        if not entry["Output File"]:
            entry["Output File"] = os.path.basename(out_path)

    return matches, logs_local, out_path
