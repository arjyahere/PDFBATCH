from fastapi import APIRouter, UploadFile, File
import pandas as pd, shutil, os

router = APIRouter(tags=["Misc"])

@router.post("/load-columns")
async def load_columns(file: UploadFile = File(...)):
    try:
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        df = pd.read_csv(temp_path, nrows=1) if temp_path.lower().endswith(".csv") else pd.read_excel(temp_path, nrows=1)
        os.remove(temp_path)
        return {"columns": list(df.columns)}
    except Exception as e:
        return {"error": str(e)}
