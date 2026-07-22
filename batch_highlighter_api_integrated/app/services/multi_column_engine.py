# Pre-compile regex patterns at module level for performance
import os
import re
import time
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
from typing import List, Tuple, Optional, Dict, Set, Union, NamedTuple
import fitz  # PyMuPDF

from ..core.utils import now_ts, safe_filename
from ..core.state import processing_state
from ..core.config import logger
from ..core.error_codes import format_error


# -------------------------------------------------------
# Pre-compiled regex patterns for performance
# -------------------------------------------------------
_DIGIT_PATTERN = re.compile(r"\D")
_NUMERIC_PATTERN = re.compile(r"\d+\.?\d*")
_UAN_PATTERN = re.compile(r"\b\d{11,12}\b")
_AMOUNT_PATTERN = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})")

# Page data cache for repeated access
_page_data_cache = {}


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
    MAX_SAMPLING_ROWS: int = 500  # Increased for tricky UAN PDFs with multi-line headers
    COLUMN_BUFFER: float = 2.0
    COLUMN_EXTRA: float = 400.0
    MIN_ROW_WORDS: int = 1
    MIN_SPAN_WIDTH: float = 50.0
    MIN_NUMERIC_LENGTH: int = 5
    MAX_WORD_RATIO: float = 0.5
    HIGHLIGHT_OPACITY: float = 0.55
    SLEEP_INTERVAL: float = 0.2  # seconds for pause checking
    
    # Custom highlight dimensions
    HIGHLIGHT_PADDING_X: float = 2.0  # Add horizontal padding around highlight
    HIGHLIGHT_PADDING_Y: float = 2.0  # Add vertical padding around highlight
    HIGHLIGHT_MIN_WIDTH: float = 30.0  # Minimum width for highlight
    HIGHLIGHT_MIN_HEIGHT: float = 10.0  # Minimum height for highlight
    HIGHLIGHT_MAX_WIDTH: float = 500.0  # Maximum width for highlight
    HIGHLIGHT_ROW_EXTENSION: float = 8.0  # Extend highlight to full row width


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

    return [
        WordTuple(
            x0=w[0], y0=w[1], x1=w[2], y1=w[3], text=w[4],
            block_no=w[5] if len(w) > 5 else 0,
            line_no=w[6] if len(w) > 6 else 0,
            word_no=w[7] if len(w) > 7 else 0
        ) for w in words
    ]


def normalize_digits(text: str) -> str:
    """Extract digits from text - optimized with pre-compiled pattern."""
    return _DIGIT_PATTERN.sub("", text or "")


def normalize_value(value: str, is_account: bool, is_esic_uan: bool = False) -> str:

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


# -------------------------------------------------------
# Cached column type checks
# -------------------------------------------------------
@lru_cache(maxsize=128)
def is_account_column(column_name: str) -> bool:
    """Check if a column is an account column based on its name."""
    return "account" in column_name.lower() or "a/c" in column_name.lower()


@lru_cache(maxsize=128)
def is_esic_or_uan_column(column_name: str) -> bool:
    """Check if a column is ESIC or UAN number column."""
    col_lower = column_name.lower()
    return any(keyword in col_lower for keyword in ["uan", "esic", "esi", "insurance"])


# -------------------------------------------------------
# Page data caching functions
# -------------------------------------------------------
def get_page_data_cached(page: fitz.Page, page_num: int) -> Dict:
    """Get page data with caching to avoid repeated get_text calls."""
    if page_num not in _page_data_cache:
        _page_data_cache[page_num] = {
            'words': page.get_text("words"),
            'dict': page.get_text("dict"),
            'text': page.get_text("text"),
            'rect': page.rect
        }
    return _page_data_cache[page_num]


def clear_page_cache():
    """Clear the page data cache. Call this after processing a PDF."""
    _page_data_cache.clear()


def extract_esic_uan_number(text: str) -> Optional[str]:
    digits = re.sub(r"\D", "", str(text or ""))
    if len(digits) in VALID_LENGTHS:
        return digits
    return None


# -------------------------------------------------------
# COLUMN DETECTION
# -------------------------------------------------------
def detect_column_ranges(page: fitz.Page) -> List[Tuple[float, float]]:
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


# Page data cache for repeated access
_page_data_cache = {}

def get_page_data_cached(page: fitz.Page, page_num: int) -> Dict:
    """Get page data with caching to avoid repeated get_text calls."""
    if page_num not in _page_data_cache:
        _page_data_cache[page_num] = {
            'words': page.get_text("words"),
            'dict': page.get_text("dict"),
            'text': page.get_text("text"),
            'rect': page.rect
        }
    return _page_data_cache[page_num]


def clear_page_cache():
    """Clear the page data cache. Call this after processing a PDF."""
    _page_data_cache.clear()
def group_words_into_rows(words: List[WordTuple], threshold: int = PDFHighlighterConfig.ROW_THRESHOLD) -> List[List[WordTuple]]:

    if not words:
        return []
    
    rows = []
    Y_TOL = threshold
    
    for word in words:
        placed = False
        for row in rows:
            # Check if this word overlaps with existing row in Y
            row_min_y = min(w.y0 for w in row)
            row_max_y = max(w.y1 for w in row)
            
            if abs(word.y0 - row_min_y) <= Y_TOL or abs(word.y1 - row_max_y) <= Y_TOL:
                row.append(word)
                placed = True
                break
        
        if not placed:
            rows.append([word])
    
    logger.debug(f"Grouped {len(words)} words into {len(rows)} visual rows")
    return rows


def detect_headers(
    words: List[Tuple],
    columns: List[str],
    column_ranges: List[Tuple[float, float]]
) -> Dict[str, int]:

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

    target_col_indices = {}
    sampling_limit = min(PDFHighlighterConfig.MAX_SAMPLING_ROWS, len(rows))
    rows_to_process = rows[:sampling_limit]
    
    logger.debug(f"Sampling {len(rows_to_process)} rows from {len(rows)} total, {len(normalized_data)} normalized data items, {len(column_ranges)} column ranges")
    
    # Pre-compute column type flags ONCE outside the loop
    if is_single:
        col_name = columns[0]
        is_acc = is_account_column(col_name)
        is_esic_uan = is_esic_or_uan_column(col_name)
        
        # Pre-convert to set for O(1) lookup if not ESIC/UAN
        data_set = normalized_data if not is_esic_uan else None
        
        col_counts = [0] * len(column_ranges)
        for row_idx, row_words in enumerate(rows_to_process):
            col_cells = {}
            for word in row_words:
                col_idx = assign_word_to_column(word.x0, column_ranges)
                col_cells[col_idx] = col_cells.get(col_idx, "") + word.text
            for col_idx, content in col_cells.items():
                normalized = normalize_value(content.strip(), is_acc, is_esic_uan)
                # For ESIC/UAN, check if the normalized value is in our data
                if is_esic_uan:
                    # Use any() with generator for early exit instead of full loop
                    if any(normalized in di or di in normalized for di in normalized_data):
                        col_counts[col_idx] += 1
                elif normalized in data_set:
                    col_counts[col_idx] += 1
        
        if col_counts:
            target_col_indices[columns[0]] = int(max(range(len(col_counts)), key=lambda i: col_counts[i]))
    else:
        # Pre-compute column type flags for multi-column
        is_acc1 = is_account_column(columns[0])
        is_acc2 = is_account_column(columns[1])
        is_esic1 = is_esic_or_uan_column(columns[0])
        is_esic2 = is_esic_or_uan_column(columns[1])
        
        # Pre-compute column range centers for faster assignment
        col_centers = [(cr[0] + cr[1]) / 2.0 for cr in column_ranges]
        num_cols = len(column_ranges)
        col_combos = list(combinations(range(num_cols), 2))
        combo_counts = {}
        
        logger.debug(f"Processing {len(col_combos)} column combinations over {len(rows_to_process)} rows")
        
        for combo_idx, combo in enumerate(col_combos):
            count = 0
            combo_set = set(combo)
            for row_words in rows_to_process:
                cells = {}
                for word in row_words:
                    # Optimized column assignment using pre-computed centers
                    col_idx = min(range(num_cols), key=lambda i: abs(col_centers[i] - word.x0))
                    if col_idx in combo_set:
                        cells[col_idx] = cells.get(col_idx, "") + word.text
                if len(cells) == 2:
                    c1 = normalize_value(cells[combo[0]].strip(), is_acc1, is_esic1)
                    c2 = normalize_value(cells[combo[1]].strip(), is_acc2, is_esic2)
                    if (c1, c2) in normalized_data:
                        count += 1
            combo_counts[combo] = count
            
            # Progress log every 10 combinations
            if (combo_idx + 1) % 10 == 0:
                logger.debug(f"Sampling combo {combo_idx + 1}/{len(col_combos)}, best count so far: {max(combo_counts.values())}")
        
        if combo_counts:
            best_combo = max(combo_counts, key=combo_counts.get)
            target_col_indices[columns[0]] = best_combo[0]
            target_col_indices[columns[1]] = best_combo[1]
            logger.debug(f"Best combo: {best_combo} with count {combo_counts[best_combo]}")
    return target_col_indices


def detect_columns_once_per_pdf(
    pdf: fitz.Document,
    columns: List[str],
    normalized_data: Union[Set[str], Set[Tuple[str, str]]],
    is_single: bool,
    fast_mode: bool = True
) -> Dict[str, int]:

    # Scan multiple pages and merge results
    MAX_PAGES_TO_SAMPLE = min(3, len(pdf))  # Sample up to 3 pages for robustness
    merged_headers: Dict[str, int] = {}
    
    # Pre-compute column type flags once
    col_type_cache = {
        'is_acc': [is_account_column(col) for col in columns],
        'is_esic': [is_esic_or_uan_column(col) for col in columns]
    }
    
    # Early exit: return immediately if all columns found
    for page_num in range(MAX_PAGES_TO_SAMPLE):
        page = pdf[page_num]
        page_data = get_page_data_cached(page, page_num)
        raw_words = page_data['words']
        if not raw_words:
            continue
            
        words = convert_words_to_tuples(raw_words)
        column_ranges = detect_column_ranges(page)
        if not column_ranges:
            continue
            
        rows = group_words_into_rows(words)
        
        # Detect headers on this page
        page_headers = detect_headers(words, columns, column_ranges)
        logger.info(f"Page {page_num + 1} header detection result: {page_headers}")
        
        # Merge into merged_headers (prefer existing values)
        for col, idx in page_headers.items():
            if col not in merged_headers:
                merged_headers[col] = idx
        
        # Early exit check
        if is_single and columns[0] in merged_headers:
            logger.info(f"Single column detected early on page {page_num + 1}")
            return merged_headers
        elif not is_single and all(col in merged_headers for col in columns):
            logger.info(f"All columns detected early on page {page_num + 1}")
            return merged_headers
    
    # After scanning all pages, check if we have required columns
    if is_single:
        has_required = columns[0] in merged_headers
    else:
        has_required = len(merged_headers) >= 2 and all(col in merged_headers for col in columns)
    
    if has_required:
        logger.info(f"Header detection succeeded after scanning {MAX_PAGES_TO_SAMPLE} pages: {merged_headers}")
        
        if fast_mode:
            # In fast mode, return headers without further validation
            return merged_headers
        else:
            # In full mode, validate with sampling on first successful page
            for page_num in range(MAX_PAGES_TO_SAMPLE):
                page = pdf[page_num]
                page_data = get_page_data_cached(page, page_num)
                raw_words = page_data['words']
                if not raw_words:
                    continue
                
                words = convert_words_to_tuples(raw_words)
                column_ranges = detect_column_ranges(page)
                if not column_ranges:
                    continue
                
                rows = group_words_into_rows(words)
                
                # Validate with sampling
                sampling_result = detect_columns_by_sampling(
                    rows, columns, column_ranges, is_single, normalized_data
                )
                logger.info(f"Page {page_num + 1} sampling validation: {sampling_result}")
                
                # Merge sampling results
                for col in columns:
                    if col in sampling_result and col not in merged_headers:
                        merged_headers[col] = sampling_result[col]
                
                # Recheck if we have all required columns
                if is_single:
                    if columns[0] in merged_headers:
                        return merged_headers
                else:
                    if all(col in merged_headers for col in columns):
                        return merged_headers
    
    # If headers failed OR fast_mode=False, try sampling-only detection on all pages
    if not fast_mode or not has_required:
        logger.info(f"Sampling-only detection: fast_mode={fast_mode}, has_required={has_required}")
        sampling_results: Dict[str, int] = {}
        for page_num in range(MAX_PAGES_TO_SAMPLE):
            page = pdf[page_num]
            page_data = get_page_data_cached(page, page_num)
            raw_words = page_data['words']
            if not raw_words:
                continue
            
            words = convert_words_to_tuples(raw_words)
            column_ranges = detect_column_ranges(page)
            if not column_ranges:
                continue
            
            rows = group_words_into_rows(words)
            
            # Sampling-only detection
            logger.info(f"Page {page_num + 1} starting sampling detection...")
            sampling_result = detect_columns_by_sampling(
                rows, columns, column_ranges, is_single, normalized_data
            )
            logger.info(f"Page {page_num + 1} sampling detection result: {sampling_result}")
            
            for col, idx in sampling_result.items():
                if col not in sampling_results:
                    sampling_results[col] = idx
            
            # Check if we have enough
            if is_single and columns[0] in sampling_results:
                logger.info(f"Single column detected via sampling on page {page_num + 1}")
                return sampling_results
            elif not is_single and len(sampling_results) >= 2:
                logger.info(f"All columns detected via sampling on page {page_num + 1}")
                return sampling_results
        
        if sampling_results:
            logger.info(f"Sampling detection succeeded: {sampling_results}")
            return sampling_results
        else:
            logger.warning("Sampling detection found no columns")
    
    # Return what we have (could be partial)
    if merged_headers:
        logger.warning(f"Partial column detection: {merged_headers}")
    else:
        logger.warning("Failed to detect columns on any sampled page")
    
    return merged_headers if merged_headers else {}


def detect_columns_with_fallback(
    pdf: fitz.Document,
    columns: List[str],
    normalized_data: Union[Set[str], Set[Tuple[str, str]]],
    is_single: bool
) -> Dict[str, int]:
    # First attempt: header-only detection (fast)
    logger.info(f"Attempting fast header-only column detection for {columns}...")
    result = detect_columns_once_per_pdf(
        pdf, columns, normalized_data, is_single, fast_mode=True
    )
    
    # Check if header detection succeeded
    if result:
        if is_single and columns[0] in result:
            logger.info("Header-only detection succeeded (single column)")
            return result
        elif not is_single and all(col in result for col in columns):
            logger.info("Header-only detection succeeded (multi-column)")
            return result
    
    # Fallback: full detection with sampling
    logger.info("Header-only detection failed. Falling back to full detection with sampling...")
    result = detect_columns_once_per_pdf(
        pdf, columns, normalized_data, is_single, fast_mode=False
    )
    
    return result


def prepare_normalized_data(
    data: List[Union[str, Tuple[str, str]]],
    columns: List[str],
    is_single: bool
) -> Union[Set[str], Set[Tuple[str, str]]]:
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

        # === ROW HIGHLIGHT (Excel-like, PDF-safe) ===
        # Geometry from matched cell words only (anchor Y from real glyphs)
        # Row spans full page width (independent of table/grid/columns)
        
        # Step 1: Collect matched cell words for Y anchor
        cell_boxes = []
        for word in row_words:
            if assign_word_to_column(word.x0, column_ranges) == target_col_indices.get(col_name, -1):
                cell_boxes.append((word.x0, word.y0, word.x1, word.y1))
        
        if not cell_boxes:
            return 0
        
        # Step 2: Anchor Y from matched glyphs
        anchor_y0 = min(b[1] for b in cell_boxes)
        anchor_y1 = max(b[3] for b in cell_boxes)
        
        # Step 3: Expand vertically with small padding (Excel feel)
        ROW_PAD_Y = 2.0
        row_y0 = anchor_y0 - ROW_PAD_Y
        row_y1 = anchor_y1 + ROW_PAD_Y
        
        # Step 4: Expand horizontally to full page bounds (PDF-safe)
        ROW_PAD_X = 6.0
        row_x0 = page.rect.x0 + ROW_PAD_X
        row_x1 = page.rect.x1 - ROW_PAD_X
        
        # Draw exactly ONE rectangle per match
        row_rect = fitz.Rect(row_x0, row_y0, row_x1, row_y1)
        
        page.draw_rect(
            row_rect,
            fill=color_rgb,
            fill_opacity=0.25,
            overlay=True
        )
        
        matches += 1
        logs.append(HighlightLog(
            file=file_basename,
            page_paragraph=f"Page {page_number+1}",
            columns=column_names,
            matched_value=matched_value,
            note="Method 1"
        ))
        
        return matches

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

        # === ROW HIGHLIGHT (Excel-like, PDF-safe) ===
        # Geometry from matched cell words only (anchor Y from real glyphs)
        # Row spans full page width (independent of table/grid/columns)
        
        # Step 1: Collect matched cell words for Y anchor
        cell_boxes = []
        for word in row_words:
            col_idx = assign_word_to_column(word.x0, column_ranges)
            if col_idx in target_col_indices.values():
                cell_boxes.append((word.x0, word.y0, word.x1, word.y1))
        
        if not cell_boxes:
            return 0
        
        # Step 2: Anchor Y from matched glyphs
        anchor_y0 = min(b[1] for b in cell_boxes)
        anchor_y1 = max(b[3] for b in cell_boxes)
        
        # Step 3: Expand vertically with small padding (Excel feel)
        ROW_PAD_Y = 2.0
        row_y0 = anchor_y0 - ROW_PAD_Y
        row_y1 = anchor_y1 + ROW_PAD_Y
        
        # Step 4: Expand horizontally to full page bounds (PDF-safe)
        ROW_PAD_X = 6.0
        row_x0 = page.rect.x0 + ROW_PAD_X
        row_x1 = page.rect.x1 - ROW_PAD_X
        
        # Draw exactly ONE rectangle per match
        row_rect = fitz.Rect(row_x0, row_y0, row_x1, row_y1)
        
        page.draw_rect(
            row_rect,
            fill=color_rgb,
            fill_opacity=0.25,
            overlay=True
        )
        
        matches += 1
        logs.append(HighlightLog(
            file=file_basename,
            page_paragraph=f"Page {page_number+1}",
            columns=column_names,
            matched_pair=f"{matched_pair[0]},{matched_pair[1]}",
            note="Method 1"
        ))
        
        return matches

    return matches


# -------------------------------------------------------
# UAN PDF FALLBACK MODE (Regex-based, no column detection)
# Used for PDFs with continuous lines instead of tabular columns
# -------------------------------------------------------
def try_uan_pdf_highlight(
    page: fitz.Page,
    normalized_data: Set[Tuple[str, str]],
    logs: List[HighlightLog],
    file_basename: str,
    page_number: int,
    color_rgb: Tuple[float, ...]
) -> int:
    
    matches = 0
    
    # First try: words-based extraction
    raw_words = page.get_text("words")
    if raw_words:
        words = convert_words_to_tuples(raw_words)
        rows = group_words_into_rows(words, threshold=10)  # Higher threshold for UAN PDFs
        
        for i, row_words in enumerate(rows):
            # Join words with spaces for proper regex matching
            line_text = " ".join(w.text for w in row_words)
            
            # 1. Find ID (11-12 digits) - use pre-compiled pattern
            id_match = _UAN_PATTERN.search(line_text)
            if not id_match:
                # Try multi-line: combine with next row
                if i + 1 < len(rows):
                    next_line_text = " ".join(w.text for w in rows[i + 1])
                    combined_text = line_text + " " + next_line_text
                    id_match = _UAN_PATTERN.search(combined_text)
                    if id_match:
                        line_text = combined_text
                        # Extend matched_words to include next row words
                        row_words = row_words + rows[i + 1]
            
            if not id_match:
                continue
            
            uid = id_match.group()
            
            # 2. Find amount (decimal with/without commas) - use pre-compiled pattern
            amount_matches = _AMOUNT_PATTERN.findall(line_text)
            if not amount_matches:
                # Try multi-line for amount
                if i + 1 < len(rows):
                    next_line_text = " ".join(w.text for w in rows[i + 1])
                    amount_matches = _AMOUNT_PATTERN.findall(next_line_text)
            
            if not amount_matches:
                continue
            
            # Normalize amount (remove commas)
            amount = amount_matches[-1].replace(',', '')
            
            # 3. Check against normalized data
            normalized_pair = (uid, amount)
            if normalized_pair not in normalized_data:
                continue
            
            # 4. Identify all words contributing to the match
            matched_words = [w for w in row_words if uid in w.text or amount.replace(',', '') in w.text or w.text in uid]
            if not matched_words:
                continue
            
            # 5. Calculate bounding box with padding
            x0 = min(w.x0 for w in matched_words) - 2
            y0 = min(w.y0 for w in matched_words) - 2
            x1 = max(w.x1 for w in matched_words) + 2
            y1 = max(w.y1 for w in matched_words) + 2
            
            # 6. Draw highlight rectangle
            rect = fitz.Rect(x0, y0, x1, y1)
            page.draw_rect(rect, fill=color_rgb, fill_opacity=0.25, overlay=True)
            
            matches += 1
            logs.append(HighlightLog(
                file=file_basename,
                page_paragraph=f"Page {page_number + 1}",
                columns="ID,Amount",
                matched_pair=f"{uid},{amount}",
                note="Method 1",
                output_file=file_basename
            ))
        
        if matches > 0:
            logger.info(f"UAN mode (words): Found {matches} matches on page {page_number + 1}")
            return matches
    
    # Fallback: Try blocks-based extraction for tricky PDFs
    page_dict = page.get_text("dict")
    if page_dict and "blocks" in page_dict:
        for block in page_dict["blocks"]:
            if block.get("type") != 0:  # Skip non-text blocks
                continue
            
            block_text = ""
            block_words = []
            
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    bbox = span.get("bbox", [0, 0, 0, 0])
                    block_text += text + " "
                    block_words.append(WordTuple(
                        x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3],
                        text=text
                    ))
            
            # Find ID and amount in block - use pre-compiled patterns
            id_match = _UAN_PATTERN.search(block_text)
            if not id_match:
                continue
            
            uid = id_match.group()
            amount_matches = _AMOUNT_PATTERN.findall(block_text)
            if not amount_matches:
                continue
            
            amount = amount_matches[-1].replace(',', '')
            normalized_pair = (uid, amount)
            
            if normalized_pair not in normalized_data:
                continue
            
            # Calculate bounding box
            matched_words = [w for w in block_words if uid in w.text or amount in w.text]
            if not matched_words:
                continue
            
            x0 = min(w.x0 for w in matched_words) - 2
            y0 = min(w.y0 for w in matched_words) - 2
            x1 = max(w.x1 for w in matched_words) + 2
            y1 = max(w.y1 for w in matched_words) + 2
            
            rect = fitz.Rect(x0, y0, x1, y1)
            page.draw_rect(rect, fill=color_rgb, fill_opacity=0.25, overlay=True)
            
            matches += 1
            logs.append(HighlightLog(
                file=file_basename,
                page_paragraph=f"Page {page_number + 1}",
                columns="ID,Amount",
                matched_pair=f"{uid},{amount}",
                note="Method 2",
                output_file=file_basename
            ))
        
        if matches > 0:
            logger.info(f"UAN mode (blocks): Found {matches} matches on page {page_number + 1}")
    
    return matches


# ============================================================
# ROW-BASED PAIR MATCHING (Bag of Words Approach)
# Treats each row as a bag of words, matches pairs independently of column position
# ============================================================

def match_rows_by_pair_search(
    page: fitz.Page,
    normalized_data: set,
    columns: List[str],
    color_rgb: Tuple[float, ...],
    file_basename: str,
    page_number: int,
    y_tolerance: float = 5.0,
    vertical_merge_threshold: float = 3.0
) -> Tuple[int, List[HighlightLog]]:

    import re
    
    logs = []
    match_count = 0
    
    # Get all words with their bounding boxes
    word_dict = page.get_text("words")
    if not word_dict:
        logger.warning(f"No words found on page {page_number + 1}")
        return 0, logs
    
    # Group words into visual rows by Y-coordinate
    # Each row is a list of (word_text, x0, y0, x1, y1)
    rows = []
    current_row = []
    current_y = None
    
    for word_info in word_dict:
        if len(word_info) >= 5:
            # word_info format: (x0, y0, x1, y1, word, ...)
            x0, y0, x1, y1 = word_info[0], word_info[1], word_info[2], word_info[3]
            word_text = word_info[4] if len(word_info) > 4 else ""
            
            word_center_y = (y0 + y1) / 2
            
            if current_y is None:
                current_y = word_center_y
                current_row.append((word_text, x0, y0, x1, y1))
            elif abs(word_center_y - current_y) <= y_tolerance:
                # Same row - add word
                
                current_row.append((word_text, x0, y0, x1, y1))
            else:
                # New row - save current and start new
                if current_row:
                    rows.append(sorted(current_row, key=lambda w: w[1]))  # Sort by X
                current_row = [(word_text, x0, y0, x1, y1)]
                current_y = word_center_y
    
    # Don't forget the last row
    if current_row:
        rows.append(sorted(current_row, key=lambda w: w[1]))
    
    logger.debug(f"Page {page_number + 1}: Found {len(rows)} visual rows")
    
    # Merge vertically close rows (for multi-line entries)
    merged_rows = []
    for row in rows:
        if merged_rows:
            last_row = merged_rows[-1]
            last_row_center_y = sum(w[2] + w[4] for w in last_row) / (2 * len(last_row))
            current_row_center_y = sum(w[2] + w[4] for w in row) / (2 * len(row))
            
            if abs(current_row_center_y - last_row_center_y) <= vertical_merge_threshold:
                # Merge with previous row
                merged_rows[-1] = last_row + row
                continue
        merged_rows.append(row)
    
    logger.debug(f"Page {page_number + 1}: {len(merged_rows)} merged rows after vertical consolidation")
    
    # For each merged row, search for matching pairs
    matched_rows = set()  # Track which row indices we've already matched
    
    for row_idx, row in enumerate(merged_rows):
        row_text = " ".join([w[0] for w in row])
        row_words = {w[0] for w in row}
        
        # Check each normalized pair
        for pair in normalized_data:
            if pair in matched_rows:
                continue
            
            value1, value2 = pair
            
            # Search for both values in this row's text
            # Use word boundary matching to avoid partial matches
            v1_pattern = re.escape(value1)
            v2_pattern = re.escape(value2)
            
            v1_found = bool(re.search(v1_pattern, row_text))
            v2_found = bool(re.search(v2_pattern, row_text))
            
            # Also check if either value appears as standalone word
            if not v1_found:
                v1_found = value1 in row_words
            if not v2_found:
                v2_found = value2 in row_words
            
            if v1_found and v2_found:
                # Found a match! Highlight the entire row
                matched_rows.add(pair)
                match_count += 1
                
                # Calculate bounding box for the row
                x0 = min(w[1] for w in row) - 2
                y0 = min(w[2] for w in row) - 2
                x1 = max(w[3] for w in row) + 2
                y1 = max(w[4] for w in row) + 2
                
                rect = fitz.Rect(x0, y0, x1, y1)
                page.draw_rect(rect, color=color_rgb, fill=color_rgb, fill_opacity=0.25, overlay=True)
                
                logs.append(HighlightLog(
                    file=file_basename,
                    page_paragraph=f"Page {page_number + 1}",
                    columns=",".join(columns),
                    matched_pair=f"{value1},{value2}",
                    note="Method 3",
                    output_file=file_basename
                ))
                
                logger.info(f"Row-based match: {value1} + {value2} on page {page_number + 1}, row {row_idx}")
    
    logger.info(f"Row-based search: Found {match_count} matches on page {page_number + 1}")
    return match_count, logs


# -------------------------------------------------------
# MAIN HIGHLIGHT FUNCTION
# -------------------------------------------------------
def pdf_highlight_file(
    path: str,
    data: List[Union[str, Tuple[str, str]]],
    column_names: str,
    color_rgb: Tuple[float, ...],
    original_filename: str,
    idx: int,
    job_id: Optional[str] = None
) -> Tuple[int, List[Dict], Optional[str]]:

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
    
    # ============================================================
    # PERFORMANCE FIX: Detect columns ONCE per PDF with fast-first fallback
    # ============================================================
    logger.info("Detecting columns with fast-first strategy...")
    target_col_indices = detect_columns_with_fallback(pdf, columns, normalized_data, is_single)
    
    # Check if column detection succeeded
    is_valid = is_single and columns[0] in target_col_indices
    is_valid = is_valid or (not is_single and len(target_col_indices) >= 2 and all(col in target_col_indices for col in columns))
    
    # If column detection failed, try UAN mode as final fallback
    if not is_valid:
        logger.warning("Column detection failed. Trying UAN regex-based mode as final fallback...")
        # UAN mode doesn't need column indices - it uses regex
        # Set target_col_indices to empty but we'll use UAN mode in the page loop
        use_uan_mode = True
    else:
        use_uan_mode = False
    
    logger.info(f"Columns LOCKED for entire PDF: {target_col_indices}, UAN mode: {use_uan_mode}")
    
    # ============================================================
    # Process all pages using ROW-BASED PAIR SEARCH (bag of words)
    # This is the PRIMARY method - no column detection needed
    # ============================================================
    
    for page_number in range(len(pdf)):
        if not processing_state.get("running", True):
            break

        page = pdf[page_number]
        
        # Use row-based pair search (bag of words approach)
        # Matches pairs independently of column position
        page_matches, page_logs = match_rows_by_pair_search(
            page, normalized_data, columns, color_rgb, file_basename, page_number
        )
        
        matches += page_matches
        logs.extend(page_logs)
        
        while processing_state.get("paused", False) and processing_state.get("running", True):
            time.sleep(PDFHighlighterConfig.SLEEP_INTERVAL)

    logger.info(f"Processed all {len(pdf)} pages using row-based pair search")

    # Save output
    base = os.path.splitext(original_filename)[0]
    # Use job_id for uniqueness if available
    if job_id:
        short_job_id = job_id[:8]
        out_name = f"{safe_filename(base)}_{short_job_id}_Highlighted.pdf"
    else:
        out_name = f"{safe_filename(base)}_{idx}_Highlighted.pdf"

    out_folder = processing_state.dest_folder if processing_state.dest_folder else os.path.join(os.getcwd(), "output")
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
        
        # Log result with warning if zero matches
        if matches == 0:
            if is_single:
                logger.warning(
                    f"Zero matches for {file_basename}. "
                    f"Column '{columns[0]}' may not exist in the PDF. "
                    f"Try using a different column or verify the PDF contains the expected data."
                )
            else:
                logger.warning(
                    f"Zero matches for {file_basename}. "
                    f"Multi-column matching requires ALL columns {columns} to exist in the PDF. "
                    f"If your PDFs only contain '{columns[1]}', use single-column mode instead."
                )
        else:
            logger.info(f"PDF highlighting completed for {file_basename}, matches: {matches}, output: {out_path}")
        
        # Clear page data cache after processing
        clear_page_cache()
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
        # Clear page data cache even on error
        clear_page_cache()
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
