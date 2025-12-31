"""
File upload routes for admin panel
"""

from fastapi import APIRouter, Request, File, UploadFile
from app.services.file_upload import file_upload_service

router = APIRouter()

@router.post("/upload/image")
async def upload_editor_image(request: Request, file: UploadFile = File(...)):
    """Upload image for Quill editor"""
    try:
        if not file or not file.filename:
            return {"success": False, "error": "No file provided"}
        
        # Use the existing file upload service
        file_info = await file_upload_service.upload_file(file)
        return {"success": True, "url": f"/{file_info['file_url']}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/upload/video")
async def upload_editor_video(request: Request, file: UploadFile = File(...)):
    """Upload video for Quill editor"""
    try:
        if not file or not file.filename:
            return {"success": False, "error": "No file provided"}
        
        # Use the existing file upload service
        file_info = await file_upload_service.upload_file(file)
        return {"success": True, "url": f"/{file_info['file_url']}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}