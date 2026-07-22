"""
PDF Highlighter Service - Wrapper class for the new decider-based architecture.

This module provides a PDFHighlighter class that delegates to the
pdf_highlighter_decider module for actual processing.
"""

from typing import List, Tuple, Dict, Optional, Union
from ..core.config import logger
from .pdf_highlighter_decider import pdf_highlight_file


class PDFHighlighter:
    """PDF Highlighter class that routes to appropriate engine based on data type."""
    
    def __init__(self):
        """Initialize the PDF highlighter service."""
        logger.info("PDFHighlighter service initialized")
    
    def highlight(
        self,
        path: str,
        data: List[Union[str, Tuple[str, str]]],
        column_names: str,
        color_rgb: Tuple[float, ...],
        original_filename: str,
        idx: int,
        job_id: Optional[str] = None,
        highlight_padding: float = 5.0
    ) -> Tuple[int, List[Dict], Optional[str]]:
        """
        Highlight values in a PDF file.
        
        Delegates to pdf_highlighter_decider which routes to:
        - Single column engine (single_column_engine.py)
        - Multi column engine (multi_column_engine.py)
        
        Args:
            path: Path to the PDF file
            data: List of values or tuples (for multi-column) to highlight
            column_names: Comma-separated column names
            color_rgb: RGB color tuple for highlighting
            original_filename: Original filename for output naming
            idx: Index for output naming
            job_id: Optional job ID for tracking
            highlight_padding: Padding around highlighted text
            
        Returns:
            Tuple of (match_count, logs, output_path)
        """
        # Parse column names
        columns = [col.strip() for col in column_names.split(',') if col.strip()]
        
        if not columns:
            logger.error("No column names provided.")
            return 0, [], None
        
        # Log processing info
        logger.info(f"PDF Highlighter: Starting for {original_filename}")
        logger.info(f"PDF Highlighter: Columns: {columns}, Data count: {len(data)}")
        
        # Prepare values based on data type
        if isinstance(data, list) and data:
            first_item = data[0]
            if isinstance(first_item, str):
                # Single column values - pass as list of strings
                values = [str(d) for d in data]
            else:
                # Multi-column tuples
                values = data
        else:
            values = []
        
        # Delegate to the decider - it handles single vs multi-column routing
        return pdf_highlight_file(
            path=path,
            values=values,
            col_name=column_names,  # Pass original column_names for comma detection
            color_rgb=color_rgb,
            original_filename=original_filename,
            idx=idx,
            job_id=job_id,
        )


# Legacy function for backward compatibility
def pdf_highlight_file_legacy(
    path: str,
    data: List[Union[str, Tuple[str, str]]],
    column_names: str,
    color_rgb: Tuple[float, ...],
    original_filename: str,
    idx: int,
    job_id: Optional[str] = None
) -> Tuple[int, List[Dict], Optional[str]]:
    """
    Legacy function for backward compatibility.
    
    Use the PDFHighlighter class instead.
    """
    highlighter = PDFHighlighter()
    return highlighter.highlight(
        path=path,
        data=data,
        column_names=column_names,
        color_rgb=color_rgb,
        original_filename=original_filename,
        idx=idx,
        job_id=job_id
    )
