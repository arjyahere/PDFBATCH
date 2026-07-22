"""
Single Column PDF Highlighter Engine

Handles:
    - UAN
    - ESIC
    - Account Number
    - Generic numeric columns

Responsibilities:
    - Column detection
    - Row grouping
    - Cell merging
    - Matching
    - Highlight drawing
    - Logging
    - Fallback detection
"""

import fitz
import os
import re
import time
from typing import List, Tuple, Optional, Dict

from ..core.utils import now_ts, safe_filename
from ..core.state import processing_state
from ..core.config import logger
from ..core.error_codes import format_error


# -------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------

UAN_LENGTH = 12
ESI_LENGTH = 10
VALID_DIGIT_LENGTHS = (UAN_LENGTH, ESI_LENGTH)


# -------------------------------------------------------
# NORMALIZERS
# -------------------------------------------------------

def normalize_digits(text: str) -> str:
    return re.sub(r"\D", "", str(text or ""))


def normalize_generic(text: str) -> str:
    s = str(text).strip().replace(",", "")
    nums = re.findall(r"\d+\.?\d*", s)
    if nums:
        val = nums[-1]
        if "." in val:
            val = val.rstrip("0").rstrip(".")
        return val
    return s


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

    ranges = []
    for i in range(len(xs) - 1):
        mid = (xs[i] + xs[i + 1]) / 2.0
        ranges.append((xs[i] - 2.0, mid + 2.0))

    ranges.append((xs[-1] - 2.0, xs[-1] + 400.0))
    return ranges


def assign_word_to_column(x0: float, column_ranges):
    for idx, (x_start, x_end) in enumerate(column_ranges):
        if x_start <= x0 <= x_end:
            return idx

    distances = [abs((a + b) / 2 - x0) for (a, b) in column_ranges]
    return int(min(range(len(distances)), key=lambda i: distances[i]))


# -------------------------------------------------------
# MAIN ENGINE
# -------------------------------------------------------

def highlight_single_column(
    path: str,
    values: List[str],
    col_name: str,
    color_rgb: Tuple[float, float, float],
    original_filename: str,
    idx: int,
    job_id: Optional[str] = None,
    highlight_padding_x: float = 0.3,
    highlight_padding_y: float = 0.5
):

    matches = 0
    logs_local: List[Dict] = []
    start_ts = now_ts()

    logger.info(f"Single Column Engine started for {os.path.basename(path)}")

    # -------------------------------------------------------
    # OPEN PDF
    # -------------------------------------------------------

    try:
        pdf = fitz.open(path)
    except Exception as e:
        error = format_error("FILE_INVALID_FORMAT", "Failed to open PDF", str(e))
        logs_local.append({
            "File": os.path.basename(path),
            "Page/Paragraph": "",
            "Column": col_name,
            "Matched Value": "",
            "Timestamp": start_ts,
            "Output File": "",
            "Note": error["message"],
            "Error Code": error["code"]
        })
        return 0, logs_local, None

    # -------------------------------------------------------
    # DETERMINE COLUMN TYPE
    # -------------------------------------------------------

    col_lower = (col_name or "").lower()

    is_account = "account" in col_lower or "a/c" in col_lower
    is_digit_mode = any(k in col_lower for k in ["uan", "esi", "esic"])

    # Normalize input values
    normalized_values = set()

    for v in values:
        if is_account:
            normalized_values.add(str(v).strip())
        elif is_digit_mode:
            d = normalize_digits(v)
            if len(d) in VALID_DIGIT_LENGTHS:
                normalized_values.add(d)
        else:
            normalized_values.add(normalize_generic(v))

    detected_values = set()

    # -------------------------------------------------------
    # PAGE LOOP
    # -------------------------------------------------------

    for page_number in range(len(pdf)):

        if not processing_state.get("running", True):
            break

        page = pdf[page_number]
        words = page.get_text("words")
        if not words:
            continue

        column_ranges = detect_column_ranges(page)
        if not column_ranges:
            continue

        # -------------------------------------------------------
        # GROUP WORDS INTO ROWS
        # -------------------------------------------------------

        rows = {}
        for (x0, y0, x1, y1, text, block, line, wno) in words:
            rows.setdefault((block, line), []).append((x0, y0, x1, y1, text))

        # -------------------------------------------------------
        # HEADER DETECTION
        # -------------------------------------------------------

        target_col_index = None
        header_zone_y = sorted([w[1] for w in words])[:10]

        for (x0, y0, x1, y1, text, block, line, wno) in words:
            if y0 <= max(header_zone_y):
                if col_lower in text.lower():
                    target_col_index = assign_word_to_column(x0, column_ranges)
                    break

        # -------------------------------------------------------
        # SAMPLING FALLBACK
        # -------------------------------------------------------

        if target_col_index is None:
            col_counts = [0] * len(column_ranges)

            for row_words in list(rows.values())[:200]:
                col_cells = {}

                for (x0, y0, x1, y1, text) in row_words:
                    col_idx = assign_word_to_column(x0, column_ranges)

                    if is_account:
                        col_cells[col_idx] = col_cells.get(col_idx, "") + text
                    elif is_digit_mode:
                        col_cells[col_idx] = col_cells.get(col_idx, "") + normalize_digits(text)
                    else:
                        col_cells[col_idx] = col_cells.get(col_idx, "") + normalize_generic(text)

                for col_idx, cell_text in col_cells.items():
                    if cell_text in normalized_values:
                        col_counts[col_idx] += 1

            target_col_index = int(max(range(len(col_counts)), key=lambda i: col_counts[i]))

        # -------------------------------------------------------
        # ROW MATCHING
        # -------------------------------------------------------

        for row_words in rows.values():

            cell_text = ""
            cell_word_boxes = []

            for (x0, y0, x1, y1, text) in row_words:
                if assign_word_to_column(x0, column_ranges) != target_col_index:
                    continue

                if is_account:
                    norm = text
                elif is_digit_mode:
                    norm = normalize_digits(text)
                else:
                    norm = normalize_generic(text)

                if not norm:
                    continue

                cell_text += norm
                cell_word_boxes.append((x0, y0, x1, y1))

            if not cell_text:
                continue

            matched_value = None
            for v in normalized_values:
                if cell_text == v or v in cell_text or cell_text in v:
                    matched_value = v
                    break

            if not matched_value or matched_value in detected_values:
                continue

            detected_values.add(matched_value)

            # Draw single rectangle for full cell
            min_x = min(w[0] for w in cell_word_boxes)
            max_x = max(w[2] for w in cell_word_boxes)
            min_y = min(w[1] for w in cell_word_boxes)
            max_y = max(w[3] for w in cell_word_boxes)

            rect = fitz.Rect(
                min_x - highlight_padding_x,
                min_y - highlight_padding_y,
                max_x + highlight_padding_x,
                max_y + highlight_padding_y
            )

            page.draw_rect(
                rect,
                color=color_rgb,
                fill=color_rgb,
                fill_opacity=0.30
            )

            matches += 1

            logs_local.append({
                "File": os.path.basename(path),
                "Page/Paragraph": f"Page {page_number+1}",
                "Column": col_name,
                "Matched Value": matched_value,
                "Timestamp": now_ts(),
                "Output File": "",
                "Note": "Method 1"
            })

        # -------------------------------------------------------
        # GLOBAL PAGE FALLBACK
        # -------------------------------------------------------

        page_text = page.get_text("text")

        for v in normalized_values:
            if v in detected_values:
                continue

            if v in page_text:
                rects = page.search_for(v)

                for rect in rects:
                    expanded = fitz.Rect(
                        rect.x0 - highlight_padding_x,
                        rect.y0 - highlight_padding_y,
                        rect.x1 + highlight_padding_x,
                        rect.y1 + highlight_padding_y
                    )

                    page.draw_rect(
                        expanded,
                        color=color_rgb,
                        fill=color_rgb,
                        fill_opacity=0.30
                    )

                    matches += 1

                detected_values.add(v)

                logs_local.append({
                    "File": os.path.basename(path),
                    "Page/Paragraph": f"Page {page_number+1}",
                    "Column": col_name,
                    "Matched Value": v,
                    "Timestamp": now_ts(),
                    "Output File": "",
                    "Note": "Method 2"
                })

        while processing_state.get("paused", False) and processing_state.get("running", True):
            time.sleep(0.2)

    # -------------------------------------------------------
    # SAVE OUTPUT
    # -------------------------------------------------------

    # Generate output filename - use job_id if available, else idx
    base = os.path.splitext(original_filename)[0]
    if job_id:
        short_job_id = job_id[:8]
        output_name = f"{safe_filename(base)}_{short_job_id}_Highlighted.pdf"
    else:
        output_name = f"{safe_filename(base)}_{idx}_Highlighted.pdf"

    dest_folder = processing_state.get("dest_folder") or os.path.join(os.getcwd(), "output")
    os.makedirs(dest_folder, exist_ok=True)

    output_path = os.path.join(dest_folder, output_name)

    if os.path.exists(output_path):
        os.remove(output_path)

    pdf.save(output_path, garbage=4, deflate=True)
    pdf.close()

    for entry in logs_local:
        entry["Output File"] = os.path.basename(output_path)

    logger.info(f"Single Column Engine completed. Matches: {matches}")

    return matches, logs_local, output_path
