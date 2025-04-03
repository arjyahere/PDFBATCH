from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
import os, urllib, mimetypes
from ..core.state import processing_state
from ..core.config import OUTPUT_FOLDER

router = APIRouter(tags=["Download"])

@router.get("/download/{filename}")
async def download_file(filename: str):
    try:
        decoded = urllib.parse.unquote(filename)
        dest = processing_state.get("dest_folder") or OUTPUT_FOLDER
        file_path = os.path.join(dest, decoded)
        if not os.path.exists(file_path):
            return JSONResponse({"error": f"File '{decoded}' not found"}, status_code=404)
        mime_type, _ = mimetypes.guess_type(file_path)
        return FileResponse(path=file_path, media_type=mime_type or "application/octet-stream", filename=decoded)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
