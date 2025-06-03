import fitz  # PyMuPDF
import os
import re
import time
from typing import List, Tuple
from ..core.utils import now_ts, safe_filename
from ..core.state import processing_state
from ..core.config import logger
from ..core.error_codes import format_error


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
def pdf_highlight_file(path, values, col_name, color_rgb, original_filename, idx):

    logger.info(f"Starting PDF highlighting for {os.path.basename(path)}, column {col_name}, values count: {len(values)}")
    matches = 0
    logs_local = []
    start = now_ts()

    try:
        pdf = fitz.open(path)
        logger.info(f"PDF opened successfully: {len(pdf)} pages")
    except Exception as e:
        logger.error(f"Failed to open PDF {path}: {e}")
        error_info = format_error(code="FILE_INVALID_FORMAT", message="Failed to open PDF", details=str(e))
        logs_local.append({
            "File": os.path.basename(path),
            "Page/Paragraph": "",
            "Column": col_name,
            "Matched Value": "",
            "Timestamp": start,
            "Output File": "",
            "Note": error_info["message"],
            "Error Code": error_info["code"]
        })
        return 0, logs_local, None

    # ---------------- NORMALIZERS ----------------
    def norm_digits(t):
        return re.sub(r"\D", "", str(t or ""))

    # Normalize input values based on column type
    is_account_col = col_name and "a/c" in col_name.lower()
    values_norm = set()
    if is_account_col:
        # For account numbers, keep full strings
        values_norm = set(values)
    else:
        # For UAN/ESI, normalize to digits and filter length
        for v in values:
            d = norm_digits(v)
            if len(d) in VALID_LENGTHS:
                values_norm.add(d)

    detected_values = set()

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
                    if is_account_col:
                        col_cells[col_idx] = col_cells.get(col_idx, "") + wtext
                    else:
                        d = norm_digits(wtext)
                        col_cells[col_idx] = col_cells.get(col_idx, "") + d

                for col_idx, merged in col_cells.items():
                    if merged in values_norm:
                        col_counts[col_idx] += 1

            target_col_index = int(max(range(len(col_counts)), key=lambda i: col_counts[i]))

        # ---------------- ROW MATCHING ----------------
        for row_words in rows.values():

            if is_account_col:
                cell_content = ""
                for (x0, y0, x1, y1, wtext) in row_words:
                    if _assign_word_to_col(x0, column_ranges) == target_col_index:
                        cell_content += wtext
            else:
                cell_content = ""
                for (x0, y0, x1, y1, wtext) in row_words:
                    if _assign_word_to_col(x0, column_ranges) == target_col_index:
                        d = norm_digits(wtext)
                        if d:
                            cell_content += d

            if not cell_content:
                continue

            matched_value = None
            for v in values_norm:
                if cell_content == v:
                    matched_value = v
                    break
                if len(cell_content) > len(v) and v in cell_content:
                    matched_value = v
                    break
                if len(cell_content) < len(v) and cell_content in v:
                    matched_value = v
                    break

            if not matched_value or matched_value in detected_values:
                continue

            detected_values.add(matched_value)

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
                error_info = format_error(code="PROCESSING_FAILED", message="Highlight error", details=str(e))
                logs_local.append({
                    "File": os.path.basename(path),
                    "Page/Paragraph": f"Page {pno+1}",
                    "Column": col_name,
                    "Matched Value": matched_value,
                    "Timestamp": now_ts(),
                    "Output File": "",
                    "Note": error_info["message"],
                    "Error Code": error_info["code"]
                })

        # ---------------- GLOBAL PAGE FAIL-SAFE ----------------
        page_text = page.get_text("text")
        if is_account_col:
            for v in values_norm:
                if v in page_text and v not in detected_values:

                    rects = page.search_for(v)
                    for rect in rects:
                        annot = page.add_highlight_annot(rect)
                        annot.set_colors(stroke=color_rgb)
                        annot.set_opacity(0.35)
                        annot.update()
                        matches += 1

                    detected_values.add(v)

                    logs_local.append({
                        "File": os.path.basename(path),
                        "Page/Paragraph": f"Page {pno+1}",
                        "Column": col_name,
                        "Matched Value": v,
                        "Timestamp": now_ts(),
                        "Output File": "",
                        "Note": "Global detection + highlight"
                    })
        else:
            page_digits = re.sub(r"\D", "", page_text)
            for v in values_norm:
                if v in page_digits and v not in detected_values:

                    rects = page.search_for(v)
                    for rect in rects:
                        annot = page.add_highlight_annot(rect)
                        annot.set_colors(stroke=color_rgb)
                        annot.set_opacity(0.35)
                        annot.update()
                        matches += 1

                    detected_values.add(v)

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
    out_name = f"{safe_filename(base)}_{idx}_Highlighted.pdf"

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

    logger.info(f"PDF highlighting completed for {os.path.basename(path)}, matches: {matches}, output: {out_path}")
    return matches, logs_local, out_path
