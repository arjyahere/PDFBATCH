from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form
import pandas as pd, shutil
from typing import List, Optional
from ..services.worker import worker_process

router = APIRouter(tags=["Process"])

@router.post("/process")
async def process_files(background_tasks: BackgroundTasks,
                        data_file: UploadFile = File(...),
                        documents: List[UploadFile] = File(...),
                        selected_column: str = Form(...),
                        selected_color: str = Form(...),
                        destination_folder: Optional[str] = Form(None)):
    try:
        data_temp = f"temp_data_{data_file.filename}"
        with open(data_temp, "wb") as buffer:
            shutil.copyfileobj(data_file.file, buffer)
        doc_temp_paths = []
        for doc in documents:
            doc_temp = f"temp_doc_{doc.filename}"
            with open(doc_temp, "wb") as buffer:
                shutil.copyfileobj(doc.file, buffer)
            doc_temp_paths.append(doc_temp)
        df = pd.read_csv(data_temp, dtype=str) if data_temp.lower().endswith(".csv") else pd.read_excel(data_temp, dtype=str)
        if selected_column not in df.columns:
            return {"error": f"Column '{selected_column}' not found"}
        values = [v.strip() for v in df[selected_column].astype(str).tolist() if v and v.lower() != "nan"]
        background_tasks.add_task(worker_process, values, doc_temp_paths, destination_folder, selected_column, selected_color)
        return {"message": "Processing started", "total_values": len(values), "total_files": len(doc_temp_paths)}
    except Exception as e:
        return {"error": str(e)}
