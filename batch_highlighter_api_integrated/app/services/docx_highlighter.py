"""
DOCX Highlighter Service for highlighting text in Word documents.
"""
import os
import re
import time
from typing import List, Dict, Optional, Tuple, Union
from docx import Document
from docx.oxml import parse_xml

from ..core.utils import now_ts, safe_filename
from ..core.state import processing_state, COLOR_PRESETS
from app.config import get_logger
from ..core.exceptions import ProcessingException, FileNotFoundException


logger = get_logger(__name__)

# Constants
UAN_LENGTH = 12
ESI_LENGTH = 10
VALID_LENGTHS = (UAN_LENGTH, ESI_LENGTH)


class DOCXHighlighter:
    """Service for highlighting text in DOCX files."""
    
    def __init__(self):
        """Initialize the DOCX highlighter service."""
        logger.info("DOCXHighlighter service initialized")
    
    @staticmethod
    def _normalize_value(val: str, is_account: bool = False) -> str:
        """Normalize a value based on type."""
        if is_account:
            return str(val).strip()
        else:
            s = str(val).strip()
            if '.' in s:
                s = s.rstrip('0').rstrip('.')
            return s
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        return re.sub(r"[^\w\s.]", "", text).strip()
    
    def _check_pause(self):
        """Check if processing should pause."""
        while processing_state["paused"] and processing_state["running"]:
            time.sleep(0.2)
    
    def highlight(
        self,
        path: str,
        data: List[Union[str, Tuple[str, str]]],
        column_names: str,
        color: str,
        original_filename: str,
        idx: int,
        job_id: str = None
    ) -> Tuple[int, List[Dict], Optional[str]]:
        """
        Highlight matching text in a DOCX file.
        
        Args:
            path: DOCX file path.
            data: Data to highlight (values or pairs).
            column_names: Column names separated by commas.
            color: Highlight color name.
            original_filename: Original filename.
            idx: Index for output naming.
            
        Returns:
            Tuple of (matches, logs, output_path).
        """
        columns = [col.strip() for col in column_names.split(',')]
        is_single = len(columns) == 1
        data_count = len(data)
        
        logger.info(
            f"Starting DOCX highlighting for {os.path.basename(path)}, "
            f"columns {columns}, data count: {data_count}, "
            f"mode: {'single' if is_single else 'pairs'}"
        )
        
        matches = 0
        logs_local = []
        start = now_ts()
        
        # Validate file exists
        if not os.path.exists(path):
            error_msg = f"DOCX file not found: {path}"
            logger.error(error_msg)
            raise FileNotFoundException(file_path=path)
        
        # Open document
        try:
            doc = Document(path)
            logger.info(f"DOCX opened successfully: {len(doc.paragraphs)} paragraphs")
        except Exception as e:
            error_msg = f"Failed to open DOCX {path}: {e}"
            logger.error(error_msg)
            raise ProcessingException(
                detail=error_msg,
                code="DOCX_OPEN_ERROR"
            )
        
        # Prepare values for matching
        if is_single:
            col_name = columns[0]
            is_account_col = col_name and "a/c" in col_name.lower()
            values_norm = set()
            if is_account_col:
                values_norm = set(data)
            else:
                for v in data:
                    d = re.sub(r"\D", "", str(v or ""))
                    if len(d) in VALID_LENGTHS:
                        values_norm.add(d)
                    else:
                        values_norm.add(self._normalize_value(v, False))
        else:
            pairs_norm = set()
            for p1, p2 in data:
                n1 = self._normalize_value(p1, "a/c" in columns[0].lower())
                n2 = self._normalize_value(p2, "a/c" in columns[1].lower())
                pairs_norm.add((n1, n2))
        
        highlighted_values = set()
        color_val = COLOR_PRESETS.get(color, COLOR_PRESETS["Yellow"])["word_val"]
        
        # Process each paragraph
        for pidx, para in enumerate(doc.paragraphs, start=1):
            if not processing_state["running"]:
                break
            
            self._check_pause()
            
            text = para.text or ""
            if not text.strip():
                continue
            
            if is_single:
                for val in values_norm:
                    flags = re.IGNORECASE if re.search(r"[A-Za-z]", val) else 0
                    pattern = r"\b" + re.escape(val) + r"\b"
                    if re.search(pattern, text, flags):
                        if val in highlighted_values:
                            continue
                        highlighted_values.add(val)
                        try:
                            for run in para.runs:
                                highlight_xml = parse_xml(
                                    rf'<w:highlight xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="{color_val}"/>')
                                rPr = run._element.get_or_add_rPr()
                                rPr.append(highlight_xml)
                            matches += 1
                            logs_local.append({
                                "File": os.path.basename(path),
                                "Page/Paragraph": f"Para {pidx}: {text[:80]}",
                                "Columns": column_names,
                                "Matched Value": val,
                                "Matched Pair": "",
                                "Timestamp": start,
                                "Output File": "",
                                "Note": "Method 1"
                            })
                        except Exception as e:
                            logs_local.append({
                                "File": os.path.basename(path),
                                "Page/Paragraph": f"Para {pidx}",
                                "Columns": column_names,
                                "Matched Value": val,
                                "Matched Pair": "",
                                "Timestamp": start,
                                "Output File": "",
                                "Note": f"Highlight error: {e}",
                                "Error Code": "HIGHLIGHT_ERROR"
                            })
            else:
                # Pairs mode
                text_normalized = self._normalize_text(text)
                for p in pairs_norm:
                    v1, v2 = p
                    if v1 in text_normalized and v2 in text_normalized:
                        if p in highlighted_values:
                            continue
                        highlighted_values.add(p)
                        try:
                            for run in para.runs:
                                highlight_xml = parse_xml(
                                    rf'<w:highlight xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="{color_val}"/>')
                                rPr = run._element.get_or_add_rPr()
                                rPr.append(highlight_xml)
                            matches += 1
                            logs_local.append({
                                "File": os.path.basename(path),
                                "Page/Paragraph": f"Para {pidx}: {text[:80]}",
                                "Columns": column_names,
                                "Matched Value": "",
                                "Matched Pair": f"{v1},{v2}",
                                "Timestamp": start,
                                "Output File": "",
                                "Note": "Method 1"
                            })
                        except Exception as e:
                            logs_local.append({
                                "File": os.path.basename(path),
                                "Page/Paragraph": f"Para {pidx}",
                                "Columns": column_names,
                                "Matched Value": "",
                                "Matched Pair": f"{v1},{v2}",
                                "Timestamp": start,
                                "Output File": "",
                                "Note": f"Highlight error: {e}",
                                "Error Code": "HIGHLIGHT_ERROR"
                            })
        
        # Save output file
        base = os.path.splitext(original_filename)[0]
        # Use job_id for uniqueness if available
        if job_id:
            short_job_id = job_id[:8]
            out_name = f"{safe_filename(base)}_{short_job_id}_Highlighted.docx"
        else:
            out_name = f"{safe_filename(base)}_{idx}_Highlighted.docx"
        out_folder = processing_state.dest_folder if processing_state.dest_folder else os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "output"
        )
        os.makedirs(out_folder, exist_ok=True)
        out_path = os.path.join(out_folder, out_name)
        
        try:
            doc.save(out_path)
        except Exception as e:
            error_msg = f"Failed to save DOCX: {e}"
            logger.error(error_msg)
            logs_local.append({
                "File": os.path.basename(path),
                "Page/Paragraph": "",
                "Columns": column_names,
                "Matched Value": "",
                "Matched Pair": "",
                "Timestamp": start,
                "Output File": "",
                "Note": error_msg,
                "Error Code": "DOCX_SAVE_ERROR"
            })
            return matches, logs_local, None
        
        # Update output file in logs
        for entry in logs_local:
            if entry["File"] == os.path.basename(path) and not entry["Output File"]:
                entry["Output File"] = os.path.basename(out_path)
        
        logger.info(
            f"DOCX highlighting completed for {os.path.basename(path)}, "
            f"matches: {matches}, output: {out_path}"
        )
        
        return matches, logs_local, out_path


# Legacy function for backward compatibility
def docx_highlight_file(
    path: str,
    data: List[Union[str, Tuple[str, str]]],
    column_names: str,
    word_color_enum: str,
    original_filename: str,
    idx: int
) -> Tuple[int, List[Dict], Optional[str]]:
    """
    Legacy function for backward compatibility.
    Use DOCXHighlighter class for new code.
    """
    highlighter = DOCXHighlighter()
    return highlighter.highlight(
        path=path,
        data=data,
        column_names=column_names,
        color=word_color_enum,
        original_filename=original_filename,
        idx=idx
    )

