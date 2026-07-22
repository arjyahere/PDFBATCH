import os
import urllib.parse
import mimetypes
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..core import get_logger, processing_state, FileNotFoundException
from ..config.settings import get_settings

logger = get_logger(__name__)
router = APIRouter(prefix="/download", tags=["Download"])

OUTPUT_FOLDER = "output"


def get_dest_folder():
    """Get the destination folder path."""
    # Check if dest_folder is set and not empty and not already OUTPUT_FOLDER
    if processing_state.dest_folder and processing_state.dest_folder.strip():
        # If it's an absolute path, use it directly
        if os.path.isabs(processing_state.dest_folder):
            return processing_state.dest_folder
        # If it's a relative path that's not just 'output', join with OUTPUT_FOLDER
        if processing_state.dest_folder != OUTPUT_FOLDER:
            return os.path.join(OUTPUT_FOLDER, processing_state.dest_folder)
    return OUTPUT_FOLDER


@router.get("/list", summary="List available files")
async def list_available_files():
    """List all available files in the output directory."""
    dest = get_dest_folder()
    
    if not os.path.exists(dest):
        return {"files": [], "folder": dest}
    
    files = []
    for f in os.listdir(dest):
        file_path = os.path.join(dest, f)
        if os.path.isfile(file_path):
            files.append({
                "name": f,
                "size": os.path.getsize(file_path),
                "url": f"/api/v1/download/{urllib.parse.quote(f)}"
            })
    
    return {"files": files, "folder": dest}


@router.get("/{filename}")
async def download_file(filename: str):
    decoded = urllib.parse.unquote(filename)
    dest = get_dest_folder()
    
    file_path = os.path.join(dest, decoded)
    
    if not os.path.exists(file_path):
        base_name = os.path.splitext(decoded)[0]
        for f in os.listdir(dest):
            if f.startswith(base_name + "_1_Highlighted"):
                file_path = os.path.join(dest, f)
                decoded = f
                break
        else:
            raise FileNotFoundException(file_path=file_path)
    
    if not os.path.exists(file_path):
        raise FileNotFoundException(file_path=file_path)
    
    mime_type, _ = mimetypes.guess_type(file_path)
    logger.info(f"Downloading file: {file_path}")
    
    return FileResponse(
        path=file_path,
        media_type=mime_type or "application/octet-stream",
        filename=decoded
    )


__all__ = ["router"]
