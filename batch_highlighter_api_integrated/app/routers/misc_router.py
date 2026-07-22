import os
import shutil
import pandas as pd
from fastapi import APIRouter, UploadFile, File

from ..core import get_logger, FileException

logger = get_logger(__name__)
router = APIRouter(prefix="/misc", tags=["Misc"])


@router.get("/health")
async def health_check():
    """Health check endpoint for frontend server detection"""
    return {"status": "healthy", "service": "batch-highlighter-api"}


@router.post("/load-columns")
async def load_columns(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            if temp_path.lower().endswith(".csv"):
                df = pd.read_csv(temp_path, nrows=1)
            else:
                df = pd.read_excel(temp_path, nrows=1)
        except Exception as e:
            raise FileException(detail=f"Failed to read file: {e}", code="FILE_READ_ERROR")
        
        os.remove(temp_path)
        logger.info(f"Loaded columns from {file.filename}: {list(df.columns)}")
        return {"columns": list(df.columns)}
        
    except FileException:
        raise


__all__ = ["router"]
