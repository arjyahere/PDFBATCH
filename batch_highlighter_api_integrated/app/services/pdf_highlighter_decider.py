from typing import List, Tuple, Optional
from ..core.config import logger


# Import engines
from .single_column_engine import highlight_single_column
from .multi_column_engine import pdf_highlight_file as multi_highlight_file


def pdf_highlight_file(
    path: str,
    values: List[str],
    col_name: str,
    color_rgb: Tuple[float, float, float],
    original_filename: str,
    idx: int,
    job_id: Optional[str] = None,
):

    logger.info("PDF Highlighter Decider invoked")

    # --------------------------------------------------
    # DECISION 1: Multi vs Single
    # --------------------------------------------------

    is_multi = False

    # Case 1: values is list of tuples → definitely multi
    if values and isinstance(values[0], (tuple, list)):
        is_multi = True

    # Case 2: Comma-separated column names → multi
    elif col_name and "," in col_name:
        is_multi = True

    # --------------------------------------------------
    # ROUTE
    # --------------------------------------------------

    if is_multi:
        logger.info("Routing to MULTI column engine")
        return multi_highlight_file(
            path=path,
            data=values,  # Use 'data' parameter for the old function
            column_names=col_name,  # Use 'column_names' parameter
            color_rgb=color_rgb,
            original_filename=original_filename,
            idx=idx,
            job_id=job_id,
        )

    else:
        logger.info("Routing to SINGLE column engine")
        return highlight_single_column(
            path=path,
            values=values,
            col_name=col_name,
            color_rgb=color_rgb,
            original_filename=original_filename,
            idx=idx,
            job_id=job_id,
        )
