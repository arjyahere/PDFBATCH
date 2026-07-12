import os
import re
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set, Union, NamedTuple
import fitz  # PyMuPDF

from ..core.utils import now_ts, safe_filename
from ..core.state import processing_state
from ..core.config import logger
from ..core.error_codes import format_error


# -------------------------------------------------------
# CONSTANTS FOR ESIC/UAN MATCHING
# -------------------------------------------------------
UAN_LENGTH = 12
ESI_LENGTH = 10
VALID_LENGTHS = (UAN_LENGTH, ESI_LENGTH)


# -------------------------------------------------------
# CONFIGURATION AND CONSTANTS
# -------------------------------------------------------
@dataclass
class PDFHighlighterConfig:
    """Configuration constants for PDF highlighting."""
    ROW_THRESHOLD: int = 15  # pixels between lines
    HEADER_CUTOFF_PERCENT: float = 0.05
    HEADER_CUTOFF_MIN: int = 10
    MAX_SAMPLING_ROWS: int = 1000  # Reduced for performance
    COLUMN_BUFFER: float = 2.0
    COLUMN_EXTRA: float = 400.0
    MIN_ROW_WORDS: int = 1
    MIN_SPAN_WIDTH: float = 50.0
    MIN_NUMERIC_LENGTH: int = 5
    MAX_WORD_RATIO: float = 0.5
    HIGHLIGHT_OPACITY: float = 0.55
    SLEEP_INTERVAL: float = 0.2  # seconds for pause checking


class WordTuple(NamedTuple):
    """Represents a word with its bounding box and metadata."""
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    block_no: int = 0
    line_no: int = 0
    word_no: int = 0


@dataclass
class HighlightLog:
    """Log entry for highlighting operations."""
    file: str
    page_paragraph: str
    columns: str
    matched_value: Optional[str] = None
    matched_pair: Optional[str] = None
    timestamp: float = field(default_factory=now_ts)
    output_file: str = ""
    note: str = ""
    error_code: str = ""


# -------------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------------
def convert_words_to_tuples(words: List[Tuple]) -> List[WordTuple]:
    """
    Convert PyMuPDF word tuples to WordTuple objects.

    Args:
        words: List of tuples from page.get_text("words").

    Returns:
        List of WordTuple objects.
    """
    return [
        WordTuple(
            x0=w[0], y0=w[1], x1=w[2], y1=w[3], text=w[4],
            block_no=w[5] if len(w) > 5 else 0,
            line_no=w[6] if len(w) > 6 else 0,
            word_no=w[7] if len(w) > 7 else 0
        ) for w in words
    ]


def normalize_digits(text: str) -> str:
    """Extract digits from text."""
    return re.sub(r"\D", "", str(text or ""))


def normalize_value(value: str, is_account: bool, is_esic_uan: bool = False) -> str:
    """
    Normalize a value based on type.

    Args:
        value: Value to normalize.
        is_account: Whether it's an account column.
        is_esic_uan: Whether it's an ESIC/UAN column.

    Returns:
        Normalized value.
    """
    s = str(value).strip().replace(',', '').replace(' ', '')

    # Handle ESIC/UAN numbers - extract digits and validate length
    if is_esic_uan:
        digits = re.sub(r"\D", "", str(value or ""))
        if len(digits) in VALID_LENGTHS:
            return digits
        return digits  # Return even if not valid length, for partial matching

    if is_account:
        # Extract all digit sequences and find the longest one >=10 digits
        digits = re.findall(r'\d+', s)
        long_digits = [d for d in digits if len(d) >= 10]
        if long_digits:
            return max(long_digits, key=len).lstrip('0') or '0'
        return s
    else:
        if any(c.isalpha() for c in s):
            return s
        numbers = re.findall(r'\d+\.?\d*', s)
        if numbers:
            val = numbers[-1]
            if '.' in val:
                val = val.rstrip('0').rstrip('.')
            return val
        return s


def is_account_column(column_name: str) -> bool:
    """Check if a column is an account column based on its name."""
    return "account" in column_name.lower() or "a/c" in column_name.lower()


def is_esic_or_uan_column(column_name: str) -> bool:
    """Check if a column is ESIC or UAN number column."""
    col_lower = column_name.lower()
    return any(keyword in col_lower for keyword in ["uan", "esic", "esi", "insurance"])


def extract_esic_uan_number(text: str) -> Optional[str]:
    """
    Extract ESIC/UAN number from text.
    Returns the number if found and valid length (10 or 12 digits), else None.
    """
    digits = re.sub(r"\D", "", str(text or ""))
    if len(digits) in VALID_LENGTHS:
        return digits
    return None


# -------------------------------------------------------
# COLUMN DETECTION
# -------------------------------------------------------
def detect_column_ranges(page: fitz.Page) -> List[Tuple[float, float]]:
    """
    Detect column ranges on a PDF page based on word positions.

    Args:
        page: PyMuPDF page object.

    Returns:
        List of tuples (x0, x1) for each column.
    """
    words = page.get_text("words")
    if not words:
        return []

    xs = sorted({round(w[0], 1) for w in words})
    if len(xs) == 1:
        return [(xs[0], xs[0] + PDFHighlighterConfig.COLUMN_EXTRA)]

    column_ranges = []
    for i in range(len(xs) - 1):
        mid = (xs[i] + xs[i + 1]) / 2.0
        column_ranges.append((xs[i] - PDFHighlighterConfig.COLUMN_BUFFER, mid + PDFHighlighterConfig.COLUMN_BUFFER))

    column_ranges.append((xs[-1] - PDFHighlighterConfig.COLUMN_BUFFER, xs[-1] + PDFHighlighterConfig.COLUMN_EXTRA))
    return column_ranges


def assign_word_to_column(x0: float, column_ranges: List[Tuple[float, float]]) -> int:
    """
    Assign a word's x-position to a column index.

    Args:
        x0: X-coordinate of the word.
        column_ranges: List of column ranges.

    Returns:
        Column index.
    """
    for idx, (cx0, cx1) in enumerate(column_ranges):
        if cx0 <= x0 <= cx1:
            return idx

    # Fallback: find closest column center
    dists = [abs((cx0 + cx1) / 2.0 - x0) for (cx0, cx1) in column_ranges]
    return int(min(range(len(dists)), key=lambda i: dists[i]))


# -------------------------------------------------------
# TEXT EXTRACTION
# -------------------------------------------------------
def extract_lines_from_page(page: fitz.Page) -> List[Tuple[str, Optional[fitz.Rect]]]:
    """
    Extract lines of text from a PDF page.

    Args:
        page: PyMuPDF page object.

    Returns:
        List of tuples (line_text, rect).
    """
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
# PAGE PROCESSING
# -------------------------------------------------------
def group_words_into_rows(words: List[WordTuple], threshold: int = PDFHighlighterConfig.ROW_THRESHOLD) -> List[List[WordTuple]]:
    """
    Group words into rows based on y-position.

    Args:
        words: List of word tuples.
        threshold: Y-threshold for grouping.

    Returns:
        List of rows, each a list of words.
    """
    words_sorted = sorted(words, key=lambda w: w.y0)
    rows = []
    current_row = []
    last_y = None
    for w in words_sorted:
        y = w.y0
        if last_y is None or y - last_y > threshold:
            if current_row:
                rows.append(current_row)
            current_row = [w]
            last_y = y
        else:
            current_row.append(w)
            last_y = max(last_y, y)
    if current_row:
        rows.append(current_row)
    return rows


def detect_headers(
    words: List[Tuple],
    columns: List[str],
    column_ranges: List[Tuple[float, float]]
) -> Dict[str, int]:
    """
    Detect header positions for columns.

    Args:
        words: Page words.
        columns: Column names.
        column_ranges: Column ranges.

    Returns:
        Dict of column name to column index.
    """
    target_col_indices = {}
    ys = [w[1] for w in words]
    header_cutoff = sorted(ys)[min(PDFHighlighterConfig.HEADER_CUTOFF_MIN, max(1, int(len(ys) * PDFHighlighterConfig.HEADER_CUTOFF_PERCENT)))] if ys else 0

    header_candidates = [
        (x0, text) for (x0, y0, _, _, text, *_) in words if y0 <= header_cutoff + PDFHighlighterConfig.COLUMN_BUFFER
    ]

    for col in columns:
        col_l = col.lower()
        keywords = []
        if "a/c" in col_l or "account" in col_l:
            keywords = ["a/c", "account", "ac", "acc"]
        elif is_esic_or_uan_column(col):
            keywords = ["uan", "esic", "esi", "insurance"]
        else:
            # For any other column name, use the column name itself and common variations
            keywords = [col_l, col_l.replace("_", " "), col_l.replace(" ", "_")]
            # Also add partial matches for longer column names
            if len(col_l) > 3:
                keywords.append(col_l[:4])  # First 4 chars
        for x0, text in header_candidates:
            text_l = str(text).lower()
            if any(kw in text_l for kw in keywords):
                target_col_indices[col] = assign_word_to_column(x0, column_ranges)
                break
    return target_col_indices


def detect_columns_by_sampling(
    rows: List[List[WordTuple]],
    columns: List[str],
    column_ranges: List[Tuple[float, float]],
    is_single: bool,
    normalized_data: Union[Set[str], Set[Tuple[str, str]]]
) -> Dict[str, int]:
    """
    Detect columns by sampling rows.

    Args:
        rows: Page rows.
        columns: Column names.
        column_ranges: Column ranges.
        is_single: Single mode.
        normalized_data: Normalized data.

    Returns:
        Dict of column to index.
    """
    target_col_indices = {}
    sampling_limit = min(PDFHighlighterConfig.MAX_SAMPLING_ROWS, len(rows))

    if is_single:
        col_name = columns[0]
        is_acc = is_account_column(col_name)
        is_esic_uan = is_esic_or_uan_column(col_name)

        col_counts = [0] * len(column_ranges)
        for row_words in rows[:sampling_limit]:
            col_cells = {}
            for word in row_words:
                col_idx = assign_word_to_column(word.x0, column_ranges)
                col_cells[col_idx] = col_cells.get(col_idx, "") + word.text
            for col_idx, content in col_cells.items():
                normalized = normalize_value(content.strip(), is_acc, is_esic_uan)
                # For ESIC/UAN, check if the normalized value is in our data
                if is_esic_uan:
                    # Check if any data item matches as substring or exact
                    for data_item in normalized_data:
                        if normalized in data_item or data_item in normalized:
                            col_counts[col_idx] += 1
                            break
                elif normalized in normalized_data:
                    col_counts[col_idx] += 1

        if col_counts:
            target_col_indices[columns[0]] = int(max(range(len(col_counts)), key=lambda i: col_counts[i]))
    else:
        from itertools import combinations
        col_combos = list(combinations(range(len(column_ranges)), 2))
        combo_counts = {}
        for combo in col_combos:
            count = 0
            for row_words in rows[:sampling_limit]:
                cells = {}
                for word in row_words:
                    col_idx = assign_word_to_column(word.x0, column_ranges)
                    if col_idx in combo:
                        cells[col_idx] = cells.get(col_idx, "") + word.text
                if len(cells) == 2:
                    is_acc1 = is_account_column(columns[0])
                    is_acc2 = is_account_column(columns[1])
                    is_esic1 = is_esic_or_uan_column(columns[0])
                    is_esic2 = is_esic_or_uan_column(columns[1])
                    c1 = normalize_value(cells[combo[0]].strip(), is_acc1, is_esic1)
                    c2 = normalize_value(cells[combo[1]].strip(), is_acc2, is_esic2)
                    if (c1, c2) in normalized_data:
                        count += 1
            combo_counts[combo] = count

        if combo_counts:
            best_combo = max(combo_counts, key=combo_counts.get)
            target_col_indices[columns[0]] = best_combo[0]
            target_col_indices[columns[1]] = best_combo[1]
    return target_col_indices


def prepare_normalized_data(
    data: List[Union[str, Tuple[str, str]]],
    columns: List[str],
    is_single: bool
) -> Union[Set[str], Set[Tuple[str, str]]]:
    """
    Prepare normalized data for matching.

    Args:
        data: Input data.
        columns: Column names.
        is_single: Single column mode.

    Returns:
        Set of normalized values or pairs.
    """
    if is_single:
        col_name = columns[0]
        is_account_col = is_account_column(col_name)
        is_esic_uan_col = is_esic_or_uan_column(col_name)
        values_norm = set()

        if is_esic_uan_col:
            # For ESIC/UAN columns, extract only valid 10 or 12 digit numbers
            for v in data:
                digits = re.sub(r"\D", "", str(v or ""))
                if len(digits) in VALID_LENGTHS:
                    values_norm.add(digits)
                else:
                    # Fallback: add normalized value anyway
                    values_norm.add(normalize_value(v, False, False))
        else:
            for v in data:
                values_norm.add(normalize_value(v, is_account_col, False))
        return values_norm
    else:
        pairs_norm = set()
        for p1, p2 in data:
            is_esic1 = is_esic_or_uan_column(columns[0])
            is_esic2 = is_esic_or_uan_column(columns[1])
            n1 = normalize_value(p1, is_account_column(columns[0]), is_esic1)
            n2 = normalize_value(p2, is_account_column(columns[1]), is_esic2)
            pairs_norm.add((n1, n2))
        return pairs_norm


def match_and_highlight_row(
    row_words: List[WordTuple],
    target_col_indices: Dict[str, int],
    column_ranges: List[Tuple[float, float]],
    normalized_data: Union[Set[str], Set[Tuple[str, str]]],
    is_single: bool,
    columns: List[str],
    page: fitz.Page,
    color_rgb: Tuple[float, ...],
    logs: List[HighlightLog],
    file_basename: str,
    column_names: str,
    page_number: int
) -> int:
    """
    Match a row and highlight if matched.

    Args:
        row_words: Words in the current row.
        target_col_indices: Mapping of column names to indices.
        column_ranges: Column ranges.
        normalized_data: Normalized data for matching.
        is_single: Whether single column mode.
        columns: Column names.
        page: PDF page object.
        color_rgb: Highlight color.
        logs: List to append logs to.
        file_basename: Base filename.
        column_names: Column names string.
        page_number: Page number.

    Returns:
        Number of matches.
    """
    matches = 0
    if is_single:
        col_name = columns[0]
        is_acc = is_account_column(col_name)
        is_esic_uan = is_esic_or_uan_column(col_name)

        cell_content_raw = ""
        for word in row_words:
            if assign_word_to_column(word.x0, column_ranges) == target_col_indices.get(col_name, -1):
                cell_content_raw += word.text

        cell_content = normalize_value(cell_content_raw.strip(), is_acc, is_esic_uan)

        if not cell_content:
            return 0

        # Check for match - for ESIC/UAN use flexible matching
        matched_value = None
        if is_esic_uan:
            # For ESIC/UAN, check if the extracted digits match any data item
            for data_item in normalized_data:
                if cell_content == data_item or data_item in cell_content or cell_content in data_item:
                    matched_value = data_item
                    break
        else:
            if cell_content in normalized_data:
                matched_value = cell_content

        if not matched_value:
            return 0

        # Highlight cell
        cell_boxes = []
        for word in row_words:
            if assign_word_to_column(word.x0, column_ranges) == target_col_indices.get(col_name, -1):
                cell_boxes.append((word.x0, word.y0, word.x1, word.y1))

        if not cell_boxes:
            return 0

        x0 = min(b[0] for b in cell_boxes)
        y0 = min(b[1] for b in cell_boxes)
        x1 = max(b[2] for b in cell_boxes)
        y1 = max(b[3] for b in cell_boxes)

        rect = fitz.Rect(x0, y0, x1, y1)
        try:
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=color_rgb)
            annot.set_opacity(PDFHighlighterConfig.HIGHLIGHT_OPACITY)
            annot.update()
            matches += 1
            logs.append(HighlightLog(
                file=file_basename,
                page_paragraph=f"Page {page_number+1}",
                columns=column_names,
                matched_value=matched_value,
                note="Cell highlighted"
            ))
        except Exception as e:
            error_info = format_error(code="PROCESSING_FAILED", message="Highlight error", details=str(e))
            logs.append(HighlightLog(
                file=file_basename,
                page_paragraph=f"Page {page_number+1}",
                columns=column_names,
                matched_value=matched_value,
                note=error_info["message"],
                error_code=error_info["code"]
            ))

    else:
        row_cells = {}
        for word in row_words:
            col_idx = assign_word_to_column(word.x0, column_ranges)
            for col_name, target_idx in target_col_indices.items():
                if col_idx == target_idx:
                    row_cells[col_name] = row_cells.get(col_name, "") + word.text

        if len(row_cells) < 2:
            return 0

        cell1_raw = row_cells.get(columns[0], "").strip()
        cell2_raw = row_cells.get(columns[1], "").strip()
        if not cell1_raw or not cell2_raw:
            return 0

        is_esic1 = is_esic_or_uan_column(columns[0])
        is_esic2 = is_esic_or_uan_column(columns[1])
        cell1 = normalize_value(cell1_raw, is_account_column(columns[0]), is_esic1)
        cell2 = normalize_value(cell2_raw, is_account_column(columns[1]), is_esic2)

        matched_pair = None
        for p in normalized_data:
            if cell1 == p[0] and cell2 == p[1]:
                matched_pair = p
                break

        if not matched_pair:
            return 0

        # Highlight cells
        cell_boxes = []
        for word in row_words:
            col_idx = assign_word_to_column(word.x0, column_ranges)
            if col_idx in target_col_indices.values():
                cell_boxes.append((word.x0, word.y0, word.x1, word.y1))

        if not cell_boxes:
            return 0

        x0 = min(b[0] for b in cell_boxes)
        y0 = min(b[1] for b in cell_boxes)
        x1 = max(b[2] for b in cell_boxes)
        y1 = max(b[3] for b in cell_boxes)

        rect = fitz.Rect(x0, y0, x1, y1)
        try:
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=color_rgb)
            annot.set_opacity(PDFHighlighterConfig.HIGHLIGHT_OPACITY)
            annot.update()
            matches += 1
            logs.append(HighlightLog(
                file=file_basename,
                page_paragraph=f"Page {page_number+1}",
                columns=column_names,
                matched_pair=f"{matched_pair[0]},{matched_pair[1]}",
                note="Cells highlighted"
            ))
        except Exception as e:
            error_info = format_error(code="PROCESSING_FAILED", message="Highlight error", details=str(e))
            logs.append(HighlightLog(
                file=file_basename,
                page_paragraph=f"Page {page_number+1}",
                columns=column_names,
                matched_pair=f"{matched_pair[0]},{matched_pair[1]}" if matched_pair else "",
                note=error_info["message"],
                error_code=error_info["code"]
            ))

    return matches


# -------------------------------------------------------
# MAIN HIGHLIGHT FUNCTION
# -------------------------------------------------------
def pdf_highlight_file(
    path: str,
    data: List[Union[str, Tuple[str, str]]],
    column_names: str,
    color_rgb: Tuple[float, ...],
    original_filename: str,
    idx: int
) -> Tuple[int, List[Dict], Optional[str]]:
    """
    Highlight data in a PDF file.

    Args:
        path: PDF file path.
        data: Data to highlight.
        column_names: Column names separated by commas.
        color_rgb: Highlight color as RGB tuple.
        original_filename: Original filename.
        idx: Index for output naming.

    Returns:
        Tuple of (matches, logs, output_path).
    """
    # Input validation
    if not data:
        logger.warning("No data provided for highlighting.")
        return 0, [], None

    if not column_names.strip():
        logger.error("No column names provided.")
        return 0, [], None

    columns = [col.strip() for col in column_names.split(',') if col.strip()]
    if not columns:
        logger.error("Invalid column names.")
        return 0, [], None

    is_single = len(columns) == 1
    if not is_single and len(columns) != 2:
        logger.error("Only single or dual column matching supported.")
        return 0, [], None

    data_count = len(data)
    logger.info(f"Starting PDF highlighting for {os.path.basename(path)}, columns {columns}, data count: {data_count}, mode: {'single' if is_single else 'pairs'}")

    matches = 0
    logs = []
    start = now_ts()
    file_basename = os.path.basename(path)

    try:
        pdf = fitz.open(path)
        logger.info(f"PDF opened successfully: {len(pdf)} pages")
    except Exception as e:
        logger.error(f"Failed to open PDF {path}: {e}")
        error_info = format_error(code="FILE_INVALID_FORMAT", message="Failed to open PDF", details=str(e))
        logs.append(HighlightLog(
            file=file_basename,
            page_paragraph="",
            columns=column_names,
            matched_pair="",
            timestamp=start,
            note=error_info["message"],
            error_code=error_info["code"]
        ))
        return 0, [_convert_log_to_dict(log) for log in logs], None

    if len(pdf) == 0:
        logger.warning("PDF has no pages.")
        pdf.close()
        return 0, [], None

    normalized_data = prepare_normalized_data(data, columns, is_single)
    logger.info(f"Normalized data sample: {list(normalized_data)[:5]} (total: {len(normalized_data)})")

    for page_number in range(len(pdf)):
        if not processing_state.get("running", True):
            break

        page = pdf[page_number]
        raw_words = page.get_text("words")
        if not raw_words:
            continue

        words = convert_words_to_tuples(raw_words)
        column_ranges = detect_column_ranges(page)
        if not column_ranges:
            continue

        rows = group_words_into_rows(words)

        target_col_indices = detect_headers(words, columns, column_ranges)
        logger.info(f"Header detection result: {target_col_indices}")

        if (is_single and not target_col_indices) or (not is_single and len(target_col_indices) < 2):
            sampling_result = detect_columns_by_sampling(rows, columns, column_ranges, is_single, normalized_data)
            target_col_indices.update(sampling_result)
            logger.info(f"Sampling detection result: {sampling_result}")

        logger.info(f"Final target columns: {target_col_indices}")

        for row_words in rows:
            matches += match_and_highlight_row(
                row_words, target_col_indices, column_ranges, normalized_data,
                is_single, columns, page, color_rgb, logs,
                file_basename, column_names, page_number
            )

        while processing_state.get("paused", False) and processing_state.get("running", True):
            time.sleep(PDFHighlighterConfig.SLEEP_INTERVAL)

    # Save output
    base = os.path.splitext(original_filename)[0]
    out_name = f"{safe_filename(base)}_{idx}_Highlighted.pdf"

    out_folder = processing_state.get("dest_folder") or os.path.join(os.getcwd(), "output")
    os.makedirs(out_folder, exist_ok=True)

    out_path = os.path.join(out_folder, out_name)

    if os.path.exists(out_path):
        os.remove(out_path)

    try:
        pdf.save(out_path, garbage=4, deflate=True)
        pdf.close()
        for log in logs:
            if not log.output_file:
                log.output_file = os.path.basename(out_path)
        logger.info(f"PDF highlighting completed for {file_basename}, matches: {matches}, output: {out_path}")
        return matches, [_convert_log_to_dict(log) for log in logs], out_path
    except Exception as e:
        pdf.close()
        logger.error(f"Failed to save PDF {out_path}: {e}")
        error_info = format_error(code="FILE_SAVE_FAILED", message="Failed to save PDF", details=str(e))
        logs.append(HighlightLog(
            file=file_basename,
            page_paragraph="",
            columns=column_names,
            timestamp=now_ts(),
            note=error_info["message"],
            error_code=error_info["code"]
        ))
        return matches, [_convert_log_to_dict(log) for log in logs], None


def _convert_log_to_dict(log: HighlightLog) -> dict:
    """Convert HighlightLog dataclass to dictionary with proper key mapping."""
    return {
        "File": log.file,
        "Page/Paragraph": log.page_paragraph,
        "Columns": log.columns,
        "Matched Value": log.matched_value if log.matched_value else "",
        "Matched Pair": log.matched_pair if log.matched_pair else "",
        "Timestamp": log.timestamp,
        "Output File": log.output_file,
        "Note": log.note,
        "Error Code": log.error_code,
    }
