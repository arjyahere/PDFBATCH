from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form, HTTPException
import pandas as pd, shutil, os
from typing import List, Optional
from ..services.worker import worker_process
from ..core.config import logger
from ..core.error_codes import format_error

router = APIRouter(tags=["Process"])

@router.post("/process")
async def process_files(background_tasks: BackgroundTasks,
                        data_file: UploadFile = File(...),
                        documents: List[UploadFile] = File(...),
                        selected_column: str = Form(...),
                        selected_color: str = Form(...),
                        destination_folder: Optional[str] = Form(None)):
    try:
        logger.info(f"Processing request with column: {selected_column}, color: {selected_color}, dest: {destination_folder}")
        logger.info(f"Data file: {data_file.filename}, Documents: {[d.filename for d in documents]}")

        data_temp = f"temp_data_{data_file.filename}"
        try:
            with open(data_temp, "wb") as buffer:
                shutil.copyfileobj(data_file.file, buffer)
            logger.info(f"Data file saved to {data_temp}")
        except PermissionError as e:
            logger.error(f"Permission denied saving data file: {e}")
            error_info = format_error(code="FILE_PERMISSION_DENIED", details=str(e))
            raise HTTPException(status_code=500, detail=error_info)
        except Exception as e:
            logger.error(f"Failed to save data file: {e}")
            error_info = format_error(code="FILE_ERROR", message="Failed to save data file", details=str(e))
            raise HTTPException(status_code=500, detail=error_info)

        doc_temp_paths = []
        for doc in documents:
            doc_temp = f"temp_doc_{doc.filename}"
            try:
                with open(doc_temp, "wb") as buffer:
                    shutil.copyfileobj(doc.file, buffer)
                doc_temp_paths.append(doc_temp)
                logger.info(f"Document saved to {doc_temp}")
            except PermissionError as e:
                logger.error(f"Permission denied saving document {doc.filename}: {e}")
                error_info = format_error(code="FILE_PERMISSION_DENIED", message=f"Failed to save document {doc.filename}", details=str(e))
                raise HTTPException(status_code=500, detail=error_info)
            except Exception as e:
                logger.error(f"Failed to save document {doc.filename}: {e}")
                error_info = format_error(code="FILE_ERROR", message=f"Failed to save document {doc.filename}", details=str(e))
                raise HTTPException(status_code=500, detail=error_info)

        try:
            if data_temp.lower().endswith(".csv"):
                df = pd.read_csv(data_temp, dtype=str)
            else:
                df = pd.read_excel(data_temp, dtype=str)
            logger.info(f"Data loaded with {len(df)} rows")
        except FileNotFoundError as e:
            logger.error(f"Data file not found: {e}")
            error_info = format_error(code="FILE_NOT_FOUND", details=str(e))
            raise HTTPException(status_code=400, detail=error_info)
        except pd.errors.EmptyDataError as e:
            logger.error(f"Data file is empty: {e}")
            error_info = format_error(code="DATA_MISSING", details=str(e))
            raise HTTPException(status_code=400, detail=error_info)
        except Exception as e:
            logger.error(f"Failed to read data file: {e}")
            error_info = format_error(code="DATA_INVALID", details=str(e))
            raise HTTPException(status_code=400, detail=error_info)

        if selected_column not in df.columns:
            logger.error(f"Column '{selected_column}' not found in data")
            error_info = format_error(code="VALIDATION_MISSING_FIELD", message=f"Column '{selected_column}' not found in data")
            raise HTTPException(status_code=400, detail=error_info)

        values = [v.strip() for v in df[selected_column].astype(str).tolist() if v and v.lower() != "nan"]
        logger.info(f"Extracted {len(values)} values from column {selected_column}")

        background_tasks.add_task(worker_process, values, doc_temp_paths, destination_folder, selected_column, selected_color)
        logger.info("Background task added for processing")
        return {"message": "Processing started", "total_values": len(values), "total_files": len(doc_temp_paths)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in process_files: {e}")
        error_info = format_error(code="SYSTEM_ERROR", details=str(e))
        raise HTTPException(status_code=500, detail=error_info)
